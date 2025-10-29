/**
 * @title AuroraClient
 * @notice MySQL client for Aurora Serverless v2 with connection pooling
 * @dev Handles historical price storage, transaction logging, and metrics persistence
 */

const mysql = require("mysql2/promise");

class AuroraClient {
    constructor(config = {}) {
        this.config = {
            host: config.host || process.env.AURORA_WRITER_ENDPOINT,
            user: config.user || process.env.AURORA_USER || "admin",
            password: config.password || process.env.AURORA_PASSWORD,
            database: config.database || "pythoracle",
            connectionLimit: config.connectionLimit || 10,
            acquireTimeout: config.acquireTimeout || 60000,
            ...config
        };

        this.pool = null;
        this.isInitialized = false;
    }

    /**
     * Initialize connection pool
     */
    async connect() {
        if (this.pool) {
            return;
        }

        try {
            this.pool = mysql.createPool({
                host: this.config.host,
                user: this.config.user,
                password: this.config.password,
                database: this.config.database,
                waitForConnections: true,
                connectionLimit: this.config.connectionLimit,
                queueLimit: 0,
                acquireTimeout: this.config.acquireTimeout,
                timeout: 60000,
                reconnect: true
            });

            console.log('✅ Aurora pool created');
            
            // Test connection
            const connection = await this.pool.getConnection();
            await connection.ping();
            connection.release();
            
            console.log('✅ Aurora connection successful');
            
            // Initialize database schema
            await this.initializeSchema();
            
        } catch (error) {
            console.error('❌ Aurora connection failed:', error.message);
            throw error;
        }
    }

    /**
     * Close connection pool
     */
    async disconnect() {
        if (this.pool) {
            await this.pool.end();
            this.pool = null;
            console.log('✅ Aurora pool closed');
        }
    }

    /**
     * Initialize database schema
     */
    async initializeSchema() {
        if (this.isInitialized) {
            return;
        }

        try {
            await this.pool.query(`
                CREATE TABLE IF NOT EXISTS price_updates (
                    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
                    feed_id VARCHAR(64) NOT NULL,
                    symbol VARCHAR(20) NOT NULL,
                    price BIGINT NOT NULL,
                    price_usd DECIMAL(20, 8) NOT NULL,
                    timestamp BIGINT UNSIGNED NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_feed_id (feed_id),
                    INDEX idx_timestamp (timestamp),
                    INDEX idx_created_at (created_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            `);

            await this.pool.query(`
                CREATE TABLE IF NOT EXISTS transactions (
                    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
                    tx_hash VARCHAR(66) NOT NULL UNIQUE,
                    feed_count TINYINT UNSIGNED NOT NULL,
                    gas_used BIGINT UNSIGNED,
                    gas_price BIGINT UNSIGNED,
                    block_number BIGINT UNSIGNED,
                    status ENUM('pending', 'confirmed', 'failed') DEFAULT 'pending',
                    error_message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    confirmed_at TIMESTAMP NULL,
                    INDEX idx_tx_hash (tx_hash),
                    INDEX idx_status (status),
                    INDEX idx_created_at (created_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            `);

            await this.pool.query(`
                CREATE TABLE IF NOT EXISTS keeper_metrics (
                    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
                    instance_id VARCHAR(64) NOT NULL,
                    region VARCHAR(20) NOT NULL,
                    is_leader BOOLEAN DEFAULT FALSE,
                    price_updates_total INT UNSIGNED DEFAULT 0,
                    successful_updates INT UNSIGNED DEFAULT 0,
                    failed_updates INT UNSIGNED DEFAULT 0,
                    avg_latency_ms FLOAT,
                    sse_connected BOOLEAN DEFAULT FALSE,
                    ws_connected BOOLEAN DEFAULT FALSE,
                    wallet_balance DECIMAL(20, 8),
                    oracle_stale BOOLEAN DEFAULT FALSE,
                    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_instance_id (instance_id),
                    INDEX idx_region (region),
                    INDEX idx_recorded_at (recorded_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            `);

            console.log('✅ Database schema initialized');
            this.isInitialized = true;
        } catch (error) {
            console.error('❌ Schema initialization failed:', error.message);
            throw error;
        }
    }

    /**
     * Store price update
     */
    async storePriceUpdate(feedId, symbol, price, priceUsd, timestamp) {
        if (!this.pool) {
            await this.connect();
        }

        try {
            await this.pool.query(`
                INSERT INTO price_updates (feed_id, symbol, price, price_usd, timestamp)
                VALUES (?, ?, ?, ?, ?)
            `, [feedId, symbol, price.toString(), priceUsd, timestamp]);

            return true;
        } catch (error) {
            console.error('❌ Failed to store price update:', error.message);
            return false;
        }
    }

    /**
     * Store price updates in batch
     */
    async storePriceUpdatesBatch(updates) {
        if (!this.pool || updates.length === 0) {
            return false;
        }

        try {
            const values = updates.map(update => [
                update.feedId,
                update.symbol,
                update.price.toString(),
                update.priceUsd,
                update.timestamp
            ]);

            await this.pool.query(`
                INSERT INTO price_updates (feed_id, symbol, price, price_usd, timestamp)
                VALUES ?
            `, [values]);

            return true;
        } catch (error) {
            console.error('❌ Failed to store price updates batch:', error.message);
            return false;
        }
    }

    /**
     * Get price history for a feed
     */
    async getPriceHistory(feedId, limit = 100) {
        if (!this.pool) {
            await this.connect();
        }

        try {
            const [rows] = await this.pool.query(`
                SELECT *
                FROM price_updates
                WHERE feed_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            `, [feedId, limit]);

            return rows;
        } catch (error) {
            console.error('❌ Failed to get price history:', error.message);
            return [];
        }
    }

    /**
     * Store transaction record
     */
    async storeTransaction(txHash, feedCount, status = 'pending') {
        if (!this.pool) {
            await this.connect();
        }

        try {
            await this.pool.query(`
                INSERT INTO transactions (tx_hash, feed_count, status)
                VALUES (?, ?, ?)
                ON DUPLICATE KEY UPDATE status = ?
            `, [txHash, feedCount, status, status]);

            return true;
        } catch (error) {
            console.error('❌ Failed to store transaction:', error.message);
            return false;
        }
    }

    /**
     * Update transaction with confirmation details
     */
    async updateTransaction(txHash, gasUsed, gasPrice, blockNumber, status = 'confirmed') {
        if (!this.pool) {
            return false;
        }

        try {
            await this.pool.query(`
                UPDATE transactions
                SET gas_used = ?, gas_price = ?, block_number = ?, status = ?, confirmed_at = NOW()
                WHERE tx_hash = ?
            `, [gasUsed, gasPrice, blockNumber, status, txHash]);

            return true;
        } catch (error) {
            console.error('❌ Failed to update transaction:', error.message);
            return false;
        }
    }

    /**
     * Mark transaction as failed
     */
    async markTransactionFailed(txHash, errorMessage) {
        if (!this.pool) {
            return false;
        }

        try {
            await this.pool.query(`
                UPDATE transactions
                SET status = 'failed', error_message = ?
                WHERE tx_hash = ?
            `, [errorMessage, txHash]);

            return true;
        } catch (error) {
            console.error('❌ Failed to mark transaction as failed:', error.message);
            return false;
        }
    }

    /**
     * Store keeper metrics
     */
    async storeKeeperMetrics(metrics) {
        if (!this.pool) {
            return false;
        }

        try {
            await this.pool.query(`
                INSERT INTO keeper_metrics (
                    instance_id, region, is_leader,
                    price_updates_total, successful_updates, failed_updates,
                    avg_latency_ms, sse_connected, ws_connected,
                    wallet_balance, oracle_stale
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            `, [
                metrics.instanceId,
                metrics.region,
                metrics.isLeader,
                metrics.priceUpdatesTotal || 0,
                metrics.successfulUpdates || 0,
                metrics.failedUpdates || 0,
                metrics.avgLatencyMs || 0,
                metrics.sseConnected || false,
                metrics.wsConnected || false,
                metrics.walletBalance || 0,
                metrics.oracleStale || false
            ]);

            return true;
        } catch (error) {
            console.error('❌ Failed to store keeper metrics:', error.message);
            return false;
        }
    }

    /**
     * Get recent metrics for a region
     */
    async getRecentMetrics(region, limit = 100) {
        if (!this.pool) {
            await this.connect();
        }

        try {
            const [rows] = await this.pool.query(`
                SELECT *
                FROM keeper_metrics
                WHERE region = ?
                ORDER BY recorded_at DESC
                LIMIT ?
            `, [region, limit]);

            return rows;
        } catch (error) {
            console.error('❌ Failed to get recent metrics:', error.message);
            return [];
        }
    }

    /**
     * Cleanup old data (run as maintenance task)
     */
    async cleanupOldData(daysToKeep = 90) {
        if (!this.pool) {
            return false;
        }

        try {
            const cutoffDate = new Date();
            cutoffDate.setDate(cutoffDate.getDate() - daysToKeep);

            await this.pool.query(`
                DELETE FROM price_updates WHERE created_at < ?
            `, [cutoffDate]);

            await this.pool.query(`
                DELETE FROM keeper_metrics WHERE recorded_at < ?
            `, [cutoffDate]);

            console.log(`✅ Cleaned up data older than ${daysToKeep} days`);
            return true;
        } catch (error) {
            console.error('❌ Failed to cleanup old data:', error.message);
            return false;
        }
    }

    /**
     * Get database statistics
     */
    async getDatabaseStats() {
        if (!this.pool) {
            await this.connect();
        }

        try {
            const [priceCount] = await this.pool.query(`
                SELECT COUNT(*) as count FROM price_updates
            `);
            
            const [txCount] = await this.pool.query(`
                SELECT COUNT(*) as count FROM transactions
            `);
            
            const [failedTxCount] = await this.pool.query(`
                SELECT COUNT(*) as count FROM transactions WHERE status = 'failed'
            `);

            return {
                priceUpdates: priceCount[0].count,
                transactions: txCount[0].count,
                failedTransactions: failedTxCount[0].count,
                successRate: txCount[0].count > 0 
                    ? ((txCount[0].count - failedTxCount[0].count) / txCount[0].count * 100).toFixed(2)
                    : 0
            };
        } catch (error) {
            console.error('❌ Failed to get database stats:', error.message);
            return null;
        }
    }
}

module.exports = AuroraClient;

