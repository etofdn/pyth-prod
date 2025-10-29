/**
 * @title StateManager
 * @notice Distributed state management for multi-region oracle keepers
 * @dev Handles leader election, nonce coordination, and price state sync via Redis
 */

const Redis = require("ioredis");
const crypto = require("crypto");

class StateManager {
    constructor(config = {}) {
        this.config = {
            redisUrl: config.redisUrl || process.env.REDIS_URL,
            region: config.region || process.env.REGION || "us-east-1",
            instanceId: config.instanceId || this.generateInstanceId(),
            leaderLeaseTime: config.leaderLeaseTime || 30, // seconds
            heartbeatInterval: config.heartbeatInterval || 10, // seconds
            noncePoolSize: config.noncePoolSize || 10,
            ...config
        };

        this.redis = null;
        this.isLeader = false;
        this.leaderInstance = null;
        this.heartbeatInterval = null;
        this.currentNonce = 0;
        
        // Cache for nonce pool
        this.noncePool = new Set();
        this.maxNonceInPool = 0;
    }

    generateInstanceId() {
        return `${this.config.region}-${crypto.randomBytes(4).toString('hex')}`;
    }

    async connect() {
        if (this.redis) {
            return;
        }

        this.redis = new Redis(this.config.redisUrl, {
            retryStrategy: (times) => {
                const delay = Math.min(times * 50, 2000);
                return delay;
            },
            maxRetriesPerRequest: 3,
            enableReadyCheck: true,
            enableOfflineQueue: false
        });

        // Connection event handlers
        this.redis.on('connect', () => {
            console.log('✅ Redis connected');
        });

        this.redis.on('error', (err) => {
            console.error('❌ Redis error:', err.message);
        });

        this.redis.on('close', () => {
            console.log('⚠️ Redis connection closed');
            this.isLeader = false;
        });

        // Wait for connection
        await this.redis.ping();
        console.log('✅ StateManager connected to Redis');
    }

    async disconnect() {
        if (this.heartbeatInterval) {
            clearInterval(this.heartbeatInterval);
            this.heartbeatInterval = null;
        }

        if (this.redis) {
            await this.redis.quit();
            this.redis = null;
        }

        console.log('✅ StateManager disconnected from Redis');
    }

    /**
     * Try to become the leader
     * Uses Redis SET with NX and EX for atomic leader election
     */
    async tryBecomeLeader() {
        if (!this.redis) {
            await this.connect();
        }

        try {
            const key = `leader:${this.config.region}`;
            const result = await this.redis.set(
                key,
                this.config.instanceId,
                'EX',
                this.config.leaderLeaseTime,
                'NX'
            );

            if (result === 'OK') {
                this.isLeader = true;
                this.leaderInstance = this.config.instanceId;
                console.log(`👑 Became leader in ${this.config.region}`);
                this.startHeartbeat();
                return true;
            } else {
                // Check current leader
                const currentLeader = await this.redis.get(key);
                this.leaderInstance = currentLeader;
                this.isLeader = (currentLeader === this.config.instanceId);
                
                if (this.isLeader) {
                    // Renew lease
                    await this.redis.expire(key, this.config.leaderLeaseTime);
                    this.startHeartbeat();
                }
                
                return this.isLeader;
            }
        } catch (error) {
            console.error('❌ Leader election failed:', error.message);
            return false;
        }
    }

    /**
     * Start heartbeat to maintain leadership
     */
    startHeartbeat() {
        if (this.heartbeatInterval) {
            clearInterval(this.heartbeatInterval);
        }

        this.heartbeatInterval = setInterval(async () => {
            if (this.isLeader) {
                await this.renewLeadership();
            } else {
                await this.tryBecomeLeader();
            }
        }, this.config.heartbeatInterval * 1000);
    }

    /**
     * Renew leadership lease
     */
    async renewLeadership() {
        if (!this.redis || !this.isLeader) {
            return false;
        }

        try {
            const key = `leader:${this.config.region}`;
            const currentLeader = await this.redis.get(key);
            
            if (currentLeader === this.config.instanceId) {
                await this.redis.expire(key, this.config.leaderLeaseTime);
                return true;
            } else {
                // Lost leadership
                this.isLeader = false;
                this.leaderInstance = currentLeader;
                console.log('⚠️ Lost leadership, current leader:', currentLeader);
                return false;
            }
        } catch (error) {
            console.error('❌ Leadership renewal failed:', error.message);
            this.isLeader = false;
            return false;
        }
    }

    /**
     * Get next nonce with distributed coordination
     */
    async getNextNonce() {
        if (!this.redis) {
            await this.connect();
        }

        try {
            // Use Redis INCR for atomic nonce generation
            const key = `nonce:${this.config.region}`;
            const nonce = await this.redis.incr(key);
            
            // Fetch nonce from blockchain if available
            const blockchainNonce = await this.getBlockchainNonce();
            
            // Use the higher of blockchain nonce or Redis nonce
            this.currentNonce = Math.max(nonce, blockchainNonce);
            
            // Update Redis to prevent conflicts
            await this.redis.set(key, this.currentNonce + 1);
            
            return this.currentNonce;
        } catch (error) {
            console.error('❌ Nonce generation failed:', error.message);
            // Fallback to local increment
            return ++this.currentNonce;
        }
    }

    /**
     * Get nonce from blockchain
     */
    async getBlockchainNonce(provider, wallet) {
        try {
            if (provider && wallet) {
                const nonce = await provider.getTransactionCount(wallet.address, 'latest');
                return nonce;
            }
            return 0;
        } catch (error) {
            console.error('❌ Failed to get blockchain nonce:', error.message);
            return 0;
        }
    }

    /**
     * Set blockchain nonce (for external call)
     */
    setBlockchainNonce(nonce) {
        this.currentNonce = nonce;
    }

    /**
     * Acquire nonce from pool
     */
    async acquireNonceFromPool() {
        if (!this.redis) {
            await this.connect();
        }

        try {
            const key = `nonce_pool:${this.config.region}`;
            const nonce = await this.redis.lpop(key);
            
            if (nonce) {
                return parseInt(nonce);
            }
            
            // Pool is empty, get new nonce
            return await this.getNextNonce();
        } catch (error) {
            console.error('❌ Nonce pool acquisition failed:', error.message);
            return await this.getNextNonce();
        }
    }

    /**
     * Release nonce back to pool (if not used)
     */
    async releaseNonceToPool(nonce) {
        if (!this.redis) {
            return;
        }

        try {
            const key = `nonce_pool:${this.config.region}`;
            const poolSize = await this.redis.llen(key);
            
            if (poolSize < this.config.noncePoolSize) {
                await this.redis.rpush(key, nonce);
            }
        } catch (error) {
            console.error('❌ Nonce pool release failed:', error.message);
        }
    }

    /**
     * Store last pushed price
     */
    async setLastPushedPrice(feedId, price) {
        if (!this.redis) {
            return;
        }

        try {
            const key = `last_price:${feedId}`;
            await this.redis.set(key, price.toString(), 'EX', 3600); // 1 hour TTL
        } catch (error) {
            console.error('❌ Failed to set last pushed price:', error.message);
        }
    }

    /**
     * Get last pushed price
     */
    async getLastPushedPrice(feedId) {
        if (!this.redis) {
            return null;
        }

        try {
            const key = `last_price:${feedId}`;
            const price = await this.redis.get(key);
            return price ? BigInt(price) : null;
        } catch (error) {
            console.error('❌ Failed to get last pushed price:', error.message);
            return null;
        }
    }

    /**
     * Store keeper health status
     */
    async updateHealthStatus(status) {
        if (!this.redis) {
            return;
        }

        try {
            const key = `health:${this.config.instanceId}`;
            const data = {
            ...status,
            timestamp: Date.now(),
            region: this.config.region
            };
            
            await this.redis.set(key, JSON.stringify(data), 'EX', 60); // 1 minute TTL
        } catch (error) {
            console.error('❌ Failed to update health status:', error.message);
        }
    }

    /**
     * Get all healthy keepers
     */
    async getHealthyKeepers() {
        if (!this.redis) {
            return [];
        }

        try {
            const keys = await this.redis.keys('health:*');
            const keepers = [];
            
            for (const key of keys) {
                const data = await this.redis.get(key);
                if (data) {
                    const health = JSON.parse(data);
                    keepers.push(health);
                }
            }
            
            return keepers;
        } catch (error) {
            console.error('❌ Failed to get healthy keepers:', error.message);
            return [];
        }
    }

    /**
     * Get current leader for a region
     */
    async getCurrentLeader(region) {
        if (!this.redis) {
            return null;
        }

        try {
            const key = `leader:${region}`;
            const leader = await this.redis.get(key);
            return leader;
        } catch (error) {
            console.error('❌ Failed to get current leader:', error.message);
            return null;
        }
    }

    /**
     * Get leader status
     */
    getLeaderStatus() {
        return {
            isLeader: this.isLeader,
            instanceId: this.config.instanceId,
            leaderInstance: this.leaderInstance,
            region: this.config.region,
            currentNonce: this.currentNonce
        };
    }
}

module.exports = StateManager;

