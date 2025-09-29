const { ethers } = require("ethers");
const { EventSource } = require("eventsource");
const winston = require("winston");
const promClient = require("prom-client");
const express = require("express");
const https = require("https");
const cron = require("node-cron");
require("dotenv").config();

/**
 * @title ProductionKeeperSSE
 * @notice Production-ready keeper with SSE streaming for near-real-time updates
 * @dev Implements high-throughput event pipeline with debouncing, monitoring, and failover
 */
class ProductionKeeperSSE {
    constructor(config = {}) {
        // Blockchain setup with WebSocket support and HTTP fallback
        this.wsRpcUrl = config.rpcUrl || process.env.RPC_URL || "wss://testnet-eto-y246d.avax-test.network/ext/bc/2hpQwDpDGEa4915WnAp6MP7qCcoP35jqUHFji7p3o9E99UBJmk/ws?token=da37bf16c0a88bb35f2e5c48bc8ce1229913fb135de21d7769a02b21f6c2b0ce";
        this.httpRpcUrl = "https://testnet-eto-y246d.avax-test.network/ext/bc/2hpQwDpDGEa4915WnAp6MP7qCcoP35jqUHFji7p3o9E99UBJmk/rpc?token=da37bf16c0a88bb35f2e5c48bc8ce1229913fb135de21d7769a02b21f6c2b0ce";
        this.useHttpFallback = false;

        // Use WebSocketProvider for better real-time connectivity
        if (this.wsRpcUrl.startsWith('ws://') || this.wsRpcUrl.startsWith('wss://')) {
            this.provider = new ethers.WebSocketProvider(this.wsRpcUrl);
            this.isWebSocketProvider = true;
        } else {
            this.provider = new ethers.JsonRpcProvider(this.wsRpcUrl);
            this.isWebSocketProvider = false;
        }

        this.wallet = new ethers.Wallet(process.env.PRIVATE_KEY, this.provider);

        // Contract setup
        this.consumerContract = new ethers.Contract(
            config.contractAddress || process.env.CONTRACT_ADDRESS || "0x36df4CF7cB10eD741Ed6EC553365cf515bc07121",
            [
                "function updatePriceFeeds(bytes32[] calldata feedIds, int64[] calldata prices, uint256[] calldata timestamps) external",
                "function getValidFeedCount() external view returns (uint256 count)",
                "function viewPrice() external view returns (uint256 price, uint256 timestamp)",
                "function isStale() external view returns (bool isStale)",
                "function getAllFeedIds() external view returns (bytes32[] memory)",
                "function getLatestPrice(bytes32 feedId) external view returns (int64 price, uint256 timestamp, bool isValid)"
            ],
            this.wallet
        );

        // MAANG feed configuration
        this.priceIds = [
            "0x78a3e3b8e676a8f73c439f5d749737034b139bbbe899ba5775216fba596607fe", // META/USD
            "0x49f6b65cb1de6b10eaf75e7c03ca029c306d0357e91b5311b175084a5ad55688", // AAPL/USD
            "0xb5d0e0fa58a1f8b81498ae670ce93c872d14434b72c364885d4fa1b257cbb07a", // AMZN/USD
            "0xb1073854ed24cbc755dc527418f52b7d271f6cc967bbf8d8129112b18860a593", // NVDA/USD
            "0x5a48c03e9b9cb337801073ed9d166817473697efff0d138874e0f6a33d6d5aa6"  // GOOGL/USD
        ];

        this.symbols = {
            "0x78a3e3b8e676a8f73c439f5d749737034b139bbbe899ba5775216fba596607fe": "META",
            "0x49f6b65cb1de6b10eaf75e7c03ca029c306d0357e91b5311b175084a5ad55688": "AAPL",
            "0xb5d0e0fa58a1f8b81498ae670ce93c872d14434b72c364885d4fa1b257cbb07a": "AMZN",
            "0xb1073854ed24cbc755dc527418f52b7d271f6cc967bbf8d8129112b18860a593": "NVDA",
            "0x5a48c03e9b9cb337801073ed9d166817473697efff0d138874e0f6a33d6d5aa6": "GOOGL"
        };

        // URLs and endpoints
        this.hermesBaseUrl = "https://hermes.pyth.network";
        this.sseUrl = `${this.hermesBaseUrl}/v2/updates/price/stream?${this.priceIds.map(id => `ids[]=${id.replace('0x', '')}`).join('&')}`;
        this.pollingUrl = `${this.hermesBaseUrl}/v2/updates/price/latest`;

        // State management
        this.priceCache = new Map(); // feedId -> {price: int64, timestamp: uint256, actualPrice: number}
        this.lastPushedPrices = new Map(); // feedId -> int64 (for change detection)
        this.lastPushTimestamp = 0;

        // Processing control
        this.debouncer = null;
        this.isProcessing = false;
        this.currentNonce = 0;
        this.pendingTxs = new Set();
        this.isSubmittingTx = false; // Prevent concurrent transaction submissions
        this.txTimeout = 5000; // 5 second timeout for transactions
        this.txDelay = 100; // 100ms delay between transactions to prevent nonce conflicts

        // Configuration
        this.debounceMs = parseInt(config.debounceMs || process.env.DEBOUNCE_MS || "1000"); // 1s default
        this.maxStaleness = parseInt(config.maxStaleness || process.env.MAX_STALENESS || "30"); // 30s
        this.retryAttempts = parseInt(config.retryAttempts || process.env.RETRY_ATTEMPTS || "3");
        this.minPriceChangePercent = parseFloat(config.minPriceChangePercent || process.env.MIN_PRICE_CHANGE_PERCENT || "0.1"); // 0.1% (disable aggressive mode)
        this.forceUpdateIntervalMs = parseInt(config.forceUpdateIntervalMs || process.env.FORCE_UPDATE_INTERVAL_MS || "300000"); // 5 min

        // SSE management
        this.sseEventSource = null;
        this.sseReconnectCount = 0;
        this.maxSseReconnects = 10;
        this.fallbackToPolling = false;
        this.pollingInterval = null;

        // WebSocket management
        this.wsReconnectCount = 0;
        this.maxWsReconnects = 10;
        this.wsReconnectInterval = null;
        this.lastWsHeartbeat = 0;

        // Setup logging and metrics
        this.setupLogging();
        this.setupMetrics();

        // Health tracking
        this.healthStatus = {
            sseConnected: false,
            wsConnected: false,
            lastPriceUpdate: 0,
            lastTxSuccess: 0,
            lastWsHeartbeat: 0,
            errorCount: 0,
            warningCount: 0,
            rpcType: this.isWebSocketProvider ? "WebSocket" : "HTTP"
        };
    }

    setupLogging() {
        this.logger = winston.createLogger({
            level: process.env.LOG_LEVEL || "debug",
            format: winston.format.combine(
                winston.format.timestamp(),
                winston.format.errors({ stack: true }),
                winston.format.json()
            ),
            defaultMeta: { service: "pyth-keeper-sse" },
            transports: [
                new winston.transports.Console({
                    format: winston.format.combine(
                        winston.format.colorize(),
                        winston.format.simple()
                    )
                }),
                new winston.transports.File({
                    filename: "logs/error.log",
                    level: "error",
                    maxsize: 10485760, // 10MB
                    maxFiles: 5
                }),
                new winston.transports.File({
                    filename: "logs/keeper.log",
                    maxsize: 10485760, // 10MB
                    maxFiles: 5
                })
            ]
        });
    }

    setupMetrics() {
        // Create registry
        this.register = new promClient.Registry();
        promClient.collectDefaultMetrics({ register: this.register });

        // Custom metrics
        this.metrics = {
            priceUpdatesTotal: new promClient.Counter({
                name: "price_updates_total",
                help: "Total price updates processed",
                registers: [this.register],
                labelNames: ["symbol", "status", "source"]
            }),

            txLatency: new promClient.Histogram({
                name: "tx_latency_seconds",
                help: "Transaction latency in seconds",
                registers: [this.register],
                buckets: [0.1, 0.5, 1, 2, 5, 10, 30]
            }),

            priceChangePercent: new promClient.Histogram({
                name: "price_change_percent",
                help: "Price change percentage",
                registers: [this.register],
                labelNames: ["symbol"],
                buckets: [0.01, 0.05, 0.1, 0.5, 1, 2, 5]
            }),

            sseConnectionStatus: new promClient.Gauge({
                name: "sse_connection_status",
                help: "SSE connection status (1=connected, 0=disconnected)",
                registers: [this.register]
            }),

            wsConnectionStatus: new promClient.Gauge({
                name: "ws_connection_status",
                help: "WebSocket RPC connection status (1=connected, 0=disconnected)",
                registers: [this.register]
            }),

            wsReconnectCount: new promClient.Counter({
                name: "ws_reconnect_total",
                help: "Total WebSocket reconnection attempts",
                registers: [this.register]
            }),

            gasCostGwei: new promClient.Histogram({
                name: "gas_cost_gwei",
                help: "Gas cost in Gwei",
                registers: [this.register],
                buckets: [10, 25, 50, 100, 200, 500, 1000]
            }),

            cacheSize: new promClient.Gauge({
                name: "price_cache_size",
                help: "Number of prices in cache",
                registers: [this.register]
            }),

            lastUpdateAge: new promClient.Gauge({
                name: "last_update_age_seconds",
                help: "Seconds since last successful update",
                registers: [this.register]
            })
        };
    }

    async start() {
        this.logger.info("🚀 Starting Production Keeper with SSE streaming...");

        try {
            // Initialize
            await this.refreshNonce();

            // Start services
            this.setupWebSocketMonitoring();
            this.startSSE();
            this.startHealthMonitoring();
            this.setupMetricsEndpoint();
            this.scheduleMaintenanceTasks();

            // Setup graceful shutdown
            this.setupGracefulShutdown();

            this.logger.info("✅ Production Keeper started successfully", {
                debounceMs: this.debounceMs,
                contractAddress: this.consumerContract.target,
                walletAddress: this.wallet.address
            });

        } catch (error) {
            this.logger.error("❌ Failed to start keeper:", error);
            process.exit(1);
        }
    }

    setupWebSocketMonitoring() {
        if (!this.isWebSocketProvider) {
            this.logger.info("📡 Using HTTP RPC provider - WebSocket monitoring disabled");
            this.healthStatus.wsConnected = true; // Consider HTTP as always connected
            this.metrics.wsConnectionStatus.set(1);
            return;
        }

        this.logger.info("🔌 Setting up WebSocket connection monitoring...");

        // Monitor WebSocket connection events
        this.provider.websocket.on('open', () => {
            this.logger.info("✅ WebSocket RPC connection established");
            this.healthStatus.wsConnected = true;
            this.healthStatus.lastWsHeartbeat = Date.now();
            this.metrics.wsConnectionStatus.set(1);
            this.wsReconnectCount = 0;

            // Clear any reconnection interval
            if (this.wsReconnectInterval) {
                clearInterval(this.wsReconnectInterval);
                this.wsReconnectInterval = null;
            }
        });

        this.provider.websocket.on('close', (code, reason) => {
            this.logger.warn("❌ WebSocket RPC connection closed", { code, reason: reason.toString() });
            this.healthStatus.wsConnected = false;
            this.metrics.wsConnectionStatus.set(0);
            this.scheduleWsReconnection();
        });

        this.provider.websocket.on('error', (error) => {
            this.logger.error("❌ WebSocket RPC connection error:", error);
            this.healthStatus.wsConnected = false;
            this.metrics.wsConnectionStatus.set(0);
            this.healthStatus.errorCount++;
        });

        // Set up periodic heartbeat to detect stale connections
        setInterval(() => {
            this.performWsHeartbeat();
        }, 30000); // Every 30 seconds

        // Initial connection status
        if (this.provider.websocket.readyState === 1) { // OPEN
            this.healthStatus.wsConnected = true;
            this.healthStatus.lastWsHeartbeat = Date.now();
            this.metrics.wsConnectionStatus.set(1);
        }
    }

    async performWsHeartbeat() {
        if (!this.isWebSocketProvider || !this.healthStatus.wsConnected) {
            return;
        }

        try {
            // Perform a lightweight RPC call to test connection
            const blockNumber = await this.provider.getBlockNumber();
            this.healthStatus.lastWsHeartbeat = Date.now();

            this.logger.debug("💓 WebSocket heartbeat successful", { blockNumber });
        } catch (error) {
            this.logger.warn("💔 WebSocket heartbeat failed:", error.message);
            this.healthStatus.wsConnected = false;
            this.metrics.wsConnectionStatus.set(0);
            this.scheduleWsReconnection();
        }
    }

    scheduleWsReconnection() {
        if (this.wsReconnectInterval || this.wsReconnectCount >= this.maxWsReconnects) {
            return;
        }

        this.wsReconnectCount++;
        this.metrics.wsReconnectCount.inc();

        const backoffMs = Math.min(1000 * Math.pow(2, this.wsReconnectCount), 30000);

        this.logger.info(`🔄 Scheduling WebSocket reconnection in ${backoffMs}ms (attempt ${this.wsReconnectCount})`);

        this.wsReconnectInterval = setTimeout(async () => {
            try {
                await this.reconnectWebSocket();
            } catch (error) {
                this.logger.error("❌ WebSocket reconnection failed:", error);
                this.scheduleWsReconnection();
            } finally {
                this.wsReconnectInterval = null;
            }
        }, backoffMs);
    }

    async reconnectWebSocket() {
        this.logger.info("🔄 Attempting WebSocket reconnection...");

        try {
            // Destroy the old provider
            if (this.provider.websocket) {
                this.provider.websocket.removeAllListeners();
                this.provider.websocket.terminate();
            }

            // Create new WebSocket provider
            const rpcUrl = process.env.RPC_URL;
            this.provider = new ethers.WebSocketProvider(rpcUrl);
            this.wallet = new ethers.Wallet(process.env.PRIVATE_KEY, this.provider);

            // Update contract instance
            this.consumerContract = this.consumerContract.connect(this.wallet);

            // Re-setup monitoring
            this.setupWebSocketMonitoring();

            this.logger.info("✅ WebSocket reconnection successful");

        } catch (error) {
            this.logger.error("❌ WebSocket reconnection failed:", error);
            throw error;
        }
    }

    startSSE() {
        if (this.sseEventSource) {
            this.sseEventSource.close();
        }

        this.logger.info("🔌 Connecting to Hermes SSE stream...", { url: this.sseUrl });

        this.sseEventSource = new EventSource(this.sseUrl);

        this.sseEventSource.onopen = () => {
            this.logger.info("✅ SSE connection established");
            this.healthStatus.sseConnected = true;
            this.metrics.sseConnectionStatus.set(1);
            this.sseReconnectCount = 0;
            this.fallbackToPolling = false;

            // Stop polling if it was running
            if (this.pollingInterval) {
                clearInterval(this.pollingInterval);
                this.pollingInterval = null;
            }
        };

        this.sseEventSource.onmessage = (event) => {
            try {
                this.processSseMessage(event.data);
            } catch (error) {
                this.logger.error("❌ SSE message processing error:", error);
                this.healthStatus.errorCount++;
            }
        };

        this.sseEventSource.onerror = (error) => {
            this.logger.error("❌ SSE connection error:", error);
            this.healthStatus.sseConnected = false;
            this.metrics.sseConnectionStatus.set(0);
            this.healthStatus.errorCount++;

            // Exponential backoff reconnection
            this.sseReconnectCount++;
            const backoffMs = Math.min(1000 * Math.pow(2, this.sseReconnectCount), 30000);

            if (this.sseReconnectCount >= this.maxSseReconnects) {
                this.logger.warn("⚠️ Max SSE reconnection attempts reached, falling back to polling");
                this.fallbackToPolling = true;
                this.startPollingFallback();
            } else {
                this.logger.info(`🔄 Reconnecting SSE in ${backoffMs}ms (attempt ${this.sseReconnectCount})`);
                setTimeout(() => this.startSSE(), backoffMs);
            }
        };
    }

    processSseMessage(data) {
        const parsed = JSON.parse(data);

        // Handle the parsed array format from Hermes SSE
        if (!parsed || !parsed.parsed || !Array.isArray(parsed.parsed)) {
            this.logger.debug("📊 Received non-price SSE message");
            return;
        }

        let updatedFeeds = 0;

        // Process each feed in the parsed array
        for (const feedData of parsed.parsed) {
            if (!feedData || !feedData.price) {
                continue;
            }

            const feedId = `0x${feedData.id}`;
            if (!this.priceIds.includes(feedId)) {
                continue; // Not one of our feeds
            }

            const rawPrice = parseInt(feedData.price.price);
            const expo = parseInt(feedData.price.expo);
            const confidence = parseInt(feedData.price.conf);
            const publishTime = parseInt(feedData.price.publish_time);

            // Calculate actual price: price * 10^expo
            const actualPrice = rawPrice * Math.pow(10, expo);

            // Convert to 8 decimal format for contract (Pyth uses 8 decimals for most assets)
            const price = Math.round(actualPrice * 1e8);
            const timestamp = Math.floor(Date.now() / 1000);

            // Validation
            if (price <= 0) {
                this.logger.warn("⚠️ Invalid price received", { feedId, price, actualPrice });
                continue;
            }

            // Store in cache
            const oldData = this.priceCache.get(feedId);
            this.priceCache.set(feedId, {
                price,
                timestamp,
                actualPrice,
                confidence,
                publishTime
            });

            // Calculate price change
            if (oldData && oldData.actualPrice > 0) {
                const changePercent = Math.abs((actualPrice - oldData.actualPrice) / oldData.actualPrice) * 100;
                this.metrics.priceChangePercent.observe({ symbol: this.symbols[feedId] }, changePercent);
            }

            this.metrics.priceUpdatesTotal.inc({
                symbol: this.symbols[feedId],
                status: "received",
                source: "sse"
            });

            this.logger.info(`📈 ${this.symbols[feedId]}: $${actualPrice.toFixed(2)} (${price})`, {
                feedId,
                confidence: (confidence / Math.pow(10, Math.abs(expo))).toFixed(4),
                publishTime
            });

            updatedFeeds++;
        }

        if (updatedFeeds > 0) {
            this.healthStatus.lastPriceUpdate = Date.now();
            this.metrics.cacheSize.set(this.priceCache.size);

            this.logger.info(`📊 Updated ${updatedFeeds} price feeds from SSE`);

            // Always push SSE updates immediately - don't check deviations
            this.logger.info("⚡ SSE UPDATE: Force pushing transaction immediately");
            this.forceTransaction();
        }
    }

    startPollingFallback() {
        if (this.pollingInterval) return; // Already polling

        this.logger.info("🔄 Starting polling fallback mechanism");

        this.pollingInterval = setInterval(async () => {
            try {
                await this.fetchLatestPricesPolling();
            } catch (error) {
                this.logger.error("❌ Polling fallback error:", error);
            }
        }, 5000); // Poll every 5 seconds
    }

    async fetchLatestPricesPolling() {
        return new Promise((resolve, reject) => {
            const priceIdsQuery = this.priceIds.map(id => `ids[]=${id.replace('0x', '')}`).join('&');
            const url = `${this.pollingUrl}?${priceIdsQuery}`;

            https.get(url, (res) => {
                let data = '';
                res.on('data', (chunk) => data += chunk);
                res.on('end', () => {
                    try {
                        const parsed = JSON.parse(data);
                        if (parsed.parsed && parsed.parsed.length > 0) {
                            for (const feed of parsed.parsed) {
                                // Process similar to SSE message
                                this.processSseMessage(JSON.stringify({
                                    id: feed.id,
                                    price: feed.price
                                }));
                            }
                        }
                        resolve(parsed);
                    } catch (error) {
                        reject(error);
                    }
                });
            }).on('error', reject);
        });
    }

    scheduleUpdate() {
        // If force mode is enabled, update immediately without debouncing
        if (this.minPriceChangePercent === 0) {
            this.logger.info("⚡ AGGRESSIVE MODE: Force pushing transaction");
            // Don't check if processing, just force it
            this.forceTransaction();
            return;
        }

        // Clear existing debouncer
        if (this.debouncer) {
            clearTimeout(this.debouncer);
        }

        // Schedule new update
        this.debouncer = setTimeout(() => {
            this.queueUpdate();
        }, this.debounceMs);
    }

    async forceTransaction() {
        try {
            const updateData = await this.prepareUpdateData();
            if (updateData.feedIds.length > 0) {
                await this.submitTxWithRetries(updateData.feedIds, updateData.prices, updateData.timestamps);
            }
        } catch (error) {
            this.logger.error("❌ Force transaction failed", { error: error.message });
        }
    }

    async queueUpdate() {
        if (this.isProcessing) {
            this.logger.debug("⏳ Update already in progress, skipping");
            return;
        }

        // Check if we have enough feeds
        const validFeeds = this.getValidFeedsCount();
        const requiredFeeds = Math.ceil(this.priceIds.length * 0.6); // Need 60% of feeds

        if (validFeeds < requiredFeeds) {
            this.logger.warn("⚠️ Insufficient valid feeds", { validFeeds, requiredFeeds });
            return;
        }

        this.isProcessing = true;

        try {
            const updateData = await this.prepareUpdateData();

            if (updateData.feedIds.length === 0) {
                this.logger.debug("📊 No price changes detected, skipping update");
                return;
            }

            await this.submitTxWithRetries(updateData.feedIds, updateData.prices, updateData.timestamps);

            this.metrics.priceUpdatesTotal.inc({ status: "pushed", source: "debounced" });
            this.healthStatus.lastTxSuccess = Date.now();
            this.lastPushTimestamp = Date.now();

            // Update last pushed prices
            for (let i = 0; i < updateData.feedIds.length; i++) {
                this.lastPushedPrices.set(updateData.feedIds[i], updateData.prices[i]);
            }

        } catch (error) {
            this.logger.error("❌ Update queue processing failed:", error);
            this.healthStatus.errorCount++;
        } finally {
            this.isProcessing = false;
        }
    }

    async prepareUpdateData() {
        const feedIds = [];
        const prices = [];
        const timestamps = [];
        const currentTime = Date.now() / 1000;

        // If MIN_PRICE_CHANGE_PERCENT is 0, force all feeds regardless of price change
        if (this.minPriceChangePercent === 0) {
            this.logger.info("🚀 AGGRESSIVE MODE: Including all feeds");
            for (const [feedId, data] of this.priceCache) {
                // Basic validity check - price must exist and be positive
                if (data.price && data.price > 0 && data.timestamp) {
                    feedIds.push(feedId);
                    prices.push(data.price);
                    timestamps.push(data.timestamp);
                }
            }
            return { feedIds, prices, timestamps };
        }

        for (const [feedId, data] of this.priceCache) {
            // Skip stale data
            if (currentTime - data.timestamp > this.maxStaleness) {
                continue;
            }

            const lastPushedPrice = this.lastPushedPrices.get(feedId);
            const shouldUpdate = this.shouldUpdatePrice(feedId, data.price, lastPushedPrice, data.actualPrice);

            if (shouldUpdate) {
                feedIds.push(feedId);
                prices.push(data.price);
                timestamps.push(data.timestamp);
            }
        }

        // Force update if it's been too long
        const timeSinceLastPush = Date.now() - this.lastPushTimestamp;
        if (feedIds.length === 0 && timeSinceLastPush > this.forceUpdateIntervalMs) {
            this.logger.info("🔄 Forcing update due to time threshold");
            for (const [feedId, data] of this.priceCache) {
                if (currentTime - data.timestamp <= this.maxStaleness) {
                    feedIds.push(feedId);
                    prices.push(data.price);
                    timestamps.push(data.timestamp);
                }
            }
        }

        // Force update if oracle is stale (regardless of price changes)
        if (feedIds.length === 0) {
            try {
                const isStale = await this.consumerContract.isStale();
                if (isStale) {
                    this.logger.info("🚨 FORCING UPDATE: Oracle is stale!");
                    for (const [feedId, data] of this.priceCache) {
                        if (currentTime - data.timestamp <= this.maxStaleness) {
                            feedIds.push(feedId);
                            prices.push(data.price);
                            timestamps.push(data.timestamp);
                        }
                    }
                }
            } catch (error) {
                this.logger.warn("⚠️ Failed to check oracle staleness:", error.message);
            }
        }

        return { feedIds, prices, timestamps };
    }

    shouldUpdatePrice(feedId, currentPrice, lastPushedPrice, actualPrice) {
        // Always update if never pushed
        if (lastPushedPrice === undefined) {
            return true;
        }

        // Check for significant price change
        if (lastPushedPrice !== currentPrice) {
            const lastActualPrice = lastPushedPrice / 1e8;
            const changePercent = Math.abs((actualPrice - lastActualPrice) / lastActualPrice) * 100;

            if (changePercent >= this.minPriceChangePercent) {
                this.logger.debug(`📊 Significant price change detected for ${this.symbols[feedId]}`, {
                    changePercent: changePercent.toFixed(4),
                    oldPrice: lastActualPrice.toFixed(2),
                    newPrice: actualPrice.toFixed(2)
                });
                return true;
            }
        }

        return false;
    }

    getValidFeedsCount() {
        const currentTime = Date.now() / 1000;
        let count = 0;

        for (const [feedId, data] of this.priceCache) {
            if (currentTime - data.timestamp <= this.maxStaleness && data.price > 0) {
                count++;
            }
        }

        return count;
    }

    async submitTxWithRetries(feedIds, prices, timestamps) {
        // Always prevent concurrent transactions to avoid nonce conflicts
        if (this.isSubmittingTx) {
            this.logger.warn("⚠️ Transaction already in progress, skipping...");
            return null;
        }
        
        this.isSubmittingTx = true;
        let attempts = 0;
        let lastError;
        let txHash = null;
        
        // Set a timeout to automatically release the lock
        const lockTimeout = setTimeout(() => {
            if (this.isSubmittingTx) {
                this.logger.warn("⚠️ Transaction lock timeout - releasing lock", {
                    pendingTxs: this.pendingTxs.size,
                    pendingTxHashes: Array.from(this.pendingTxs)
                });
                this.isSubmittingTx = false;
                // Also clear any pending transactions
                this.pendingTxs.clear();
            }
        }, this.txTimeout);

        try {
            while (attempts < this.retryAttempts) {
            const startTime = Date.now();

            try {
                // Enhanced nonce management - get next sequential nonce
                const nonce = await this.getNextNonce();
                
                // Get current fee data with EIP-1559 support
                const feeData = await this.provider.getFeeData();
                
                // Debug fee data
                this.logger.debug("📊 Raw fee data:", {
                    gasPrice: feeData.gasPrice?.toString(),
                    maxFeePerGas: feeData.maxFeePerGas?.toString(),
                    maxPriorityFeePerGas: feeData.maxPriorityFeePerGas?.toString(),
                    lastBaseFeePerGas: feeData.lastBaseFeePerGas?.toString()
                });
                
                // Enhanced gas estimation
                const gasEstimate = await this.estimateGas(feedIds, prices, timestamps);
                const gasLimit = BigInt(gasEstimate) * BigInt(130) / BigInt(100); // 30% buffer
                
                // Smart gas pricing strategy
                const gasConfig = await this.getOptimalGasConfig(feeData);
                
                this.logger.info(`📤 Submitting transaction (attempt ${attempts + 1})`, {
                    feedCount: feedIds.length,
                    nonce,
                    gasLimit: gasLimit.toString(),
                    gasPrice: gasConfig.gasPrice?.toString(),
                    maxFeePerGas: gasConfig.maxFeePerGas?.toString(),
                    maxPriorityFeePerGas: gasConfig.maxPriorityFeePerGas?.toString(),
                    feeData: {
                        gasPrice: feeData.gasPrice?.toString(),
                        maxFeePerGas: feeData.maxFeePerGas?.toString(),
                        maxPriorityFeePerGas: feeData.maxPriorityFeePerGas?.toString()
                    }
                });

                // Debug the transaction parameters
                this.logger.debug("📤 Transaction parameters:", {
                    nonce: nonce.toString(),
                    gasLimit: gasLimit.toString(),
                    gasConfig: {
                        gasPrice: gasConfig.gasPrice?.toString(),
                        maxFeePerGas: gasConfig.maxFeePerGas?.toString(),
                        maxPriorityFeePerGas: gasConfig.maxPriorityFeePerGas?.toString()
                    },
                    feedIds: feedIds.length,
                    prices: prices.slice(0, 3), // Show first 3 prices
                    timestamps: timestamps.slice(0, 3) // Show first 3 timestamps
                });

                const tx = await this.consumerContract.updatePriceFeeds(feedIds, prices, timestamps, {
                    nonce,
                    ...gasConfig,
                    gasLimit
                });

                txHash = tx.hash;
                this.pendingTxs.add(tx.hash);
                this.logger.info(`✅ Transaction submitted: ${tx.hash}`);
                
                // Log pending transactions for debugging
                this.logger.debug(`📊 Pending transactions: ${this.pendingTxs.size}`, Array.from(this.pendingTxs));

                   // Enhanced transaction monitoring
                   const receipt = await this.waitForTransactionConfirmation(tx, attempts);
                   this.pendingTxs.delete(tx.hash);
                   
                   // Handle timeout case - consider it successful and move on
                   if (!receipt) {
                       this.logger.warn(`⏰ Transaction timed out after 1s but submitted: ${tx.hash} - moving to next`);
                       // Consider it successful - transaction was submitted, blockchain will process it
                       this.metrics.txLatency.observe((Date.now() - startTime) / 1000);
                       this.healthStatus.lastTxSuccess = Date.now();
                       // Small delay to prevent nonce conflicts
                       await new Promise(resolve => setTimeout(resolve, this.txDelay));
                       return { hash: tx.hash, status: 'timeout_submitted' };
                   }

                const latency = (Date.now() - startTime) / 1000;
                this.metrics.txLatency.observe(latency);
                
                // Record gas metrics
                if (gasConfig.gasPrice) {
                    this.metrics.gasCostGwei.observe(Number(gasConfig.gasPrice) / 1e9);
                } else if (gasConfig.maxFeePerGas) {
                    this.metrics.gasCostGwei.observe(Number(gasConfig.maxFeePerGas) / 1e9);
                }

                this.logger.info(`🎉 Transaction confirmed`, {
                    hash: tx.hash,
                    blockNumber: receipt.blockNumber,
                    gasUsed: receipt.gasUsed.toString(),
                    gasLimit: gasLimit.toString(),
                    efficiency: `${((Number(receipt.gasUsed) / Number(gasLimit)) * 100).toFixed(1)}%`,
                    latency: `${latency.toFixed(2)}s`
                });

                    // Small delay to prevent nonce conflicts
                    await new Promise(resolve => setTimeout(resolve, this.txDelay));
                    return receipt;

                } catch (error) {
                attempts++;
                lastError = error;

                // Enhanced error analysis
                const errorInfo = this.analyzeTransactionError(error);
                
                this.logger.warn(`⚠️ Transaction attempt ${attempts} failed:`, {
                    error: error.message,
                    code: error.code,
                    reason: errorInfo.reason,
                    recoverable: errorInfo.recoverable
                });

                // Handle specific error types
                if (errorInfo.reason === 'NONCE_TOO_LOW' || errorInfo.reason === 'NONCE_TOO_HIGH') {
                    await this.refreshNonce();
                } else if (errorInfo.reason === 'INSUFFICIENT_FUNDS') {
                    this.logger.error("🚨 CRITICAL: Insufficient funds for transaction!");
                    throw error; // Don't retry this
                } else if (errorInfo.reason === 'GAS_ESTIMATION_FAILED') {
                    this.logger.warn("⚠️ Gas estimation failed, using fallback gas limit");
                }

                // Switch to HTTP fallback if WebSocket is having issues
                if (this.isWebSocketProvider && !this.useHttpFallback && 
                    (errorInfo.reason === 'NETWORK_ERROR' || errorInfo.reason === 'TIMEOUT' || 
                     error.message.includes('WebSocket') || error.message.includes('connection'))) {
                    try {
                        await this.switchToHttpFallback();
                        this.logger.info("🔄 Retrying transaction with HTTP fallback");
                    } catch (fallbackError) {
                        this.logger.error("❌ Failed to switch to HTTP fallback:", fallbackError.message);
                    }
                }

                if (attempts < this.retryAttempts && errorInfo.recoverable) {
                    const backoffMs = Math.min(Math.pow(2, attempts) * 1000, 30000); // Max 30s
                    this.logger.info(`⏳ Retrying in ${backoffMs}ms...`);
                    await new Promise(resolve => setTimeout(resolve, backoffMs));
                } else if (!errorInfo.recoverable) {
                    throw error; // Don't retry non-recoverable errors
                }
            }
        }

        throw new Error(`Transaction failed after ${this.retryAttempts} attempts: ${lastError.message}`);
        } finally {
            clearTimeout(lockTimeout);
            this.isSubmittingTx = false;
            // Clean up pending transaction if it was added
            if (txHash) {
                this.pendingTxs.delete(txHash);
            }
        }
    }

    async refreshNonce() {
        try {
            // Get latest nonce (not pending) to avoid conflicts
            const confirmedNonce = await this.provider.getTransactionCount(this.wallet.address, "latest");
            this.currentNonce = confirmedNonce;
            this.logger.debug(`📊 Nonce refreshed (confirmed): ${this.currentNonce}`);
            return this.currentNonce;
        } catch (error) {
            this.logger.error("❌ Failed to refresh nonce:", error);
            throw error;
        }
    }

    async getNextNonce() {
        // Get fresh nonce from blockchain (latest only)
        const blockchainNonce = await this.provider.getTransactionCount(this.wallet.address, "latest");
        
        // Use the higher of blockchain nonce or our tracked nonce
        const nextNonce = Math.max(blockchainNonce, this.currentNonce);
        
        // Increment for next transaction
        this.currentNonce = nextNonce + 1;
        
        this.logger.debug(`📊 Nonce: blockchain=${blockchainNonce}, tracked=${this.currentNonce - 1}, next=${nextNonce}`);
        return nextNonce;
    }

    async switchToHttpFallback() {
        if (this.useHttpFallback) {
            return; // Already using HTTP fallback
        }

        this.logger.warn("🔄 Switching to HTTP RPC fallback due to WebSocket issues");
        this.useHttpFallback = true;
        
        try {
            // Close WebSocket connection if it exists
            if (this.isWebSocketProvider && this.provider.websocket) {
                this.provider.websocket.terminate();
            }

            // Create new HTTP provider
            this.provider = new ethers.JsonRpcProvider(this.httpRpcUrl);
            this.isWebSocketProvider = false;
            this.wallet = new ethers.Wallet(process.env.PRIVATE_KEY, this.provider);
            this.consumerContract = this.consumerContract.connect(this.wallet);

            this.logger.info("✅ Successfully switched to HTTP RPC fallback");
            this.healthStatus.rpcType = "HTTP";
        } catch (error) {
            this.logger.error("❌ Failed to switch to HTTP fallback:", error.message);
            throw error;
        }
    }

    async estimateGas(feedIds, prices, timestamps) {
        try {
            // Try to estimate gas for the transaction
            const gasEstimate = await this.consumerContract.updatePriceFeeds.estimateGas(
                feedIds, 
                prices, 
                timestamps
            );
            this.logger.debug(`📊 Gas estimate successful: ${gasEstimate.toString()}`);
            return gasEstimate;
        } catch (error) {
            this.logger.warn("⚠️ Gas estimation failed, using fallback:", error.message);
            // Fallback gas limit based on number of feeds
            const feedCount = feedIds ? feedIds.length : 5; // Default to 5 feeds
            const fallbackGas = 200000 + (feedCount * 50000);
            this.logger.debug(`📊 Using fallback gas limit: ${fallbackGas} (${feedCount} feeds)`);
            return BigInt(fallbackGas);
        }
    }

    async getOptimalGasConfig(feeData) {
        try {
            // Check if network supports EIP-1559
            if (feeData.maxFeePerGas && feeData.maxPriorityFeePerGas) {
                // Validate and convert to numbers safely
                const maxFeeNum = Number(feeData.maxFeePerGas);
                const priorityFeeNum = Number(feeData.maxPriorityFeePerGas);
                
                if (isNaN(maxFeeNum) || isNaN(priorityFeeNum) || maxFeeNum <= 0 || priorityFeeNum <= 0) {
                    throw new Error("Invalid EIP-1559 fee data");
                }
                
                // Use EIP-1559 pricing with 20% buffer for faster confirmation
                const maxFeePerGas = BigInt(Math.floor(maxFeeNum * 1.2));
                const maxPriorityFeePerGas = BigInt(Math.floor(priorityFeeNum * 1.2));
                
                return {
                    maxFeePerGas,
                    maxPriorityFeePerGas
                };
            } else if (feeData.gasPrice) {
                // Validate and convert legacy gas price
                const gasPriceNum = Number(feeData.gasPrice);
                
                if (isNaN(gasPriceNum) || gasPriceNum <= 0) {
                    throw new Error("Invalid legacy gas price");
                }
                
                // Fallback to legacy gas pricing with 20% buffer
                const gasPrice = BigInt(Math.floor(gasPriceNum * 1.2));
                return { gasPrice };
            } else {
                throw new Error("No valid gas pricing data available");
            }
        } catch (error) {
            this.logger.warn("⚠️ Failed to get optimal gas config, using fallback:", error.message);
            // Fallback to conservative gas pricing - use a fixed gas price for ETO testnet
            const fallbackGasPrice = ethers.parseUnits("25", "gwei"); // 25 gwei for ETO testnet
            this.logger.debug(`📊 Using fallback gas price: ${fallbackGasPrice.toString()}`);
            return { gasPrice: fallbackGasPrice };
        }
    }

    async waitForTransactionConfirmation(tx, attempt = 0) {
        try {
            // Ultra-aggressive timeout - only wait 1 second for confirmation
            const timeout = 1000; // 1 second timeout
            this.logger.debug(`⏳ Waiting for transaction confirmation: ${tx.hash} (attempt ${attempt + 1}) - 1s timeout`);
            const receipt = await tx.wait(1, timeout);
            this.logger.debug(`✅ Transaction confirmed: ${tx.hash}`);
            return receipt;
        } catch (error) {
            if (error.code === 'TIMEOUT') {
                this.logger.warn(`⏰ Transaction confirmation timeout for ${tx.hash} after 1s - moving to next`);
                // Don't throw error, just return null to indicate timeout
                return null;
            }
            this.logger.error(`❌ Transaction confirmation error for ${tx.hash}:`, error.message);
            throw error;
        }
    }

    analyzeTransactionError(error) {
        const errorMessage = error.message.toLowerCase();
        
        // Nonce errors
        if (errorMessage.includes('nonce too low') || errorMessage.includes('nonce has already been used')) {
            return { reason: 'NONCE_TOO_LOW', recoverable: true };
        }
        if (errorMessage.includes('nonce too high')) {
            return { reason: 'NONCE_TOO_HIGH', recoverable: true };
        }
        
        // Gas errors
        if (errorMessage.includes('gas required exceeds allowance') || 
            errorMessage.includes('intrinsic gas too low') ||
            errorMessage.includes('out of gas')) {
            return { reason: 'GAS_ESTIMATION_FAILED', recoverable: true };
        }
        
        // Fee errors
        if (errorMessage.includes('insufficient funds') || 
            errorMessage.includes('gas price too low') ||
            errorMessage.includes('replacement fee too low')) {
            return { reason: 'INSUFFICIENT_FUNDS', recoverable: false };
        }
        
        // Network errors
        if (errorMessage.includes('network error') || 
            errorMessage.includes('timeout') ||
            errorMessage.includes('connection')) {
            return { reason: 'NETWORK_ERROR', recoverable: true };
        }
        
        // Contract errors
        if (errorMessage.includes('execution reverted') ||
            errorMessage.includes('insufficientvalidfeeds')) {
            return { reason: 'CONTRACT_ERROR', recoverable: false };
        }
        
        // Default to recoverable for unknown errors
        return { reason: 'UNKNOWN_ERROR', recoverable: true };
    }

    startHealthMonitoring() {
        // Main health check every minute
        cron.schedule('* * * * *', async () => {
            try {
                await this.performHealthCheck();
            } catch (error) {
                this.logger.error("❌ Health check failed:", error);
                this.healthStatus.errorCount++;
            }
        });

        // Update metrics every 10 seconds
        setInterval(() => {
            this.updateMetrics();
        }, 10000);
    }

    async performHealthCheck() {
        const start = Date.now();

        try {
            // Parallel health checks
            const [balance, validFeeds, isStale, priceData] = await Promise.all([
                this.provider.getBalance(this.wallet.address),
                this.consumerContract.getValidFeedCount(),
                this.consumerContract.isStale(),
                this.consumerContract.viewPrice()
            ]);

            const healthData = {
                timestamp: new Date().toISOString(),
                balance: ethers.formatEther(balance),
                onChainValidFeeds: Number(validFeeds),
                cacheValidFeeds: this.getValidFeedsCount(),
                isStale,
                onChainPrice: Number(priceData[0]),
                onChainTimestamp: Number(priceData[1]),
                pendingTxs: this.pendingTxs.size,
                cacheSize: this.priceCache.size,
                sseConnected: this.healthStatus.sseConnected,
                wsConnected: this.healthStatus.wsConnected,
                rpcType: this.isWebSocketProvider ? 'WebSocket' : 'HTTP',
                lastPriceUpdate: this.healthStatus.lastPriceUpdate,
                lastTxSuccess: this.healthStatus.lastTxSuccess,
                lastWsHeartbeat: this.healthStatus.lastWsHeartbeat,
                errorCount: this.healthStatus.errorCount,
                checkLatency: Date.now() - start
            };

            this.logger.info("🏥 Health Check", healthData);

            // Alerts for critical issues
            if (parseFloat(healthData.balance) < 1) {
                this.logger.error("🚨 CRITICAL: Low balance!", { balance: healthData.balance });
            }

            if (isStale) {
                this.logger.warn("⚠️ WARNING: Oracle is stale!");
            }

            if (!this.healthStatus.sseConnected && !this.fallbackToPolling) {
                this.logger.warn("⚠️ WARNING: SSE disconnected but no fallback active");
            }

            // Reset error count if everything is healthy
            if (healthData.checkLatency < 5000 && !isStale && this.healthStatus.sseConnected) {
                this.healthStatus.errorCount = 0;
            }

        } catch (error) {
            this.logger.error("❌ Health check execution failed:", error);
            this.healthStatus.errorCount++;
        }
    }

    updateMetrics() {
        const now = Date.now();

        // Update age metrics
        if (this.healthStatus.lastTxSuccess > 0) {
            this.metrics.lastUpdateAge.set((now - this.healthStatus.lastTxSuccess) / 1000);
        }

        // Update cache size
        this.metrics.cacheSize.set(this.priceCache.size);

        // Update SSE connection status
        this.metrics.sseConnectionStatus.set(this.healthStatus.sseConnected ? 1 : 0);
    }

    setupMetricsEndpoint() {
        const app = express();
        const port = process.env.METRICS_PORT || 9090;

        app.get('/metrics', async (req, res) => {
            try {
                res.set('Content-Type', this.register.contentType);
                const metrics = await this.register.metrics();
                res.end(metrics);
            } catch (error) {
                res.status(500).end(error.message);
            }
        });

        app.get('/health', (req, res) => {
            const isHealthy = (this.healthStatus.sseConnected || this.fallbackToPolling) &&
                             (this.healthStatus.wsConnected || !this.isWebSocketProvider);
            res.status(isHealthy ? 200 : 503).json({
                status: isHealthy ? 'healthy' : 'unhealthy',
                ...this.healthStatus,
                rpcType: this.isWebSocketProvider ? 'WebSocket' : 'HTTP',
                uptime: process.uptime(),
                cacheSize: this.priceCache.size,
                pendingTxs: this.pendingTxs.size
            });
        });

        app.get('/status', async (req, res) => {
            try {
                const [balance, validFeeds, isStale] = await Promise.all([
                    this.provider.getBalance(this.wallet.address),
                    this.consumerContract.getValidFeedCount(),
                    this.consumerContract.isStale()
                ]);

                res.json({
                    keeper: {
                        balance: ethers.formatEther(balance),
                        sseConnected: this.healthStatus.sseConnected,
                        wsConnected: this.healthStatus.wsConnected,
                        rpcType: this.isWebSocketProvider ? 'WebSocket' : 'HTTP',
                        fallbackMode: this.fallbackToPolling,
                        cacheSize: this.priceCache.size,
                        pendingTxs: this.pendingTxs.size,
                        wsReconnectCount: this.wsReconnectCount,
                        lastWsHeartbeat: this.healthStatus.lastWsHeartbeat
                    },
                    oracle: {
                        validFeeds: Number(validFeeds),
                        isStale,
                        contractAddress: this.consumerContract.target
                    },
                    feeds: Array.from(this.priceCache.entries()).map(([feedId, data]) => ({
                        symbol: this.symbols[feedId],
                        feedId,
                        price: data.actualPrice,
                        timestamp: data.timestamp,
                        age: Math.floor(Date.now() / 1000) - data.timestamp
                    }))
                });
            } catch (error) {
                res.status(500).json({ error: error.message });
            }
        });

        app.listen(port, () => {
            this.logger.info(`📊 Metrics and health endpoints available at :${port}`);
        });
    }

    scheduleMaintenanceTasks() {
        // Nonce refresh every 5 minutes
        cron.schedule('*/5 * * * *', async () => {
            try {
                await this.refreshNonce();
            } catch (error) {
                this.logger.error("❌ Scheduled nonce refresh failed:", error);
            }
        });

        // Cache cleanup every hour
        cron.schedule('0 * * * *', () => {
            this.cleanupStaleCache();
        });

        // Log rotation and cleanup
        cron.schedule('0 0 * * *', () => {
            this.logger.info("🧹 Daily maintenance tasks completed");
        });
    }

    cleanupStaleCache() {
        const currentTime = Date.now() / 1000;
        const staleThreshold = this.maxStaleness * 2; // Remove data older than 2x max staleness
        let cleanedCount = 0;

        for (const [feedId, data] of this.priceCache) {
            if (currentTime - data.timestamp > staleThreshold) {
                this.priceCache.delete(feedId);
                cleanedCount++;
            }
        }

        if (cleanedCount > 0) {
            this.logger.info(`🧹 Cleaned ${cleanedCount} stale cache entries`);
        }
    }

    setupGracefulShutdown() {
        const shutdown = async (signal) => {
            this.logger.info(`🛑 Received ${signal}, shutting down gracefully...`);

            // Close SSE connection
            if (this.sseEventSource) {
                this.sseEventSource.close();
            }

            // Close WebSocket connection
            if (this.isWebSocketProvider && this.provider.websocket) {
                this.provider.websocket.removeAllListeners();
                this.provider.websocket.terminate();
            }

            // Clear intervals
            if (this.pollingInterval) {
                clearInterval(this.pollingInterval);
            }

            if (this.wsReconnectInterval) {
                clearTimeout(this.wsReconnectInterval);
            }

            if (this.debouncer) {
                clearTimeout(this.debouncer);
            }

            // Wait for pending transactions
            if (this.pendingTxs.size > 0) {
                this.logger.info(`⏳ Waiting for ${this.pendingTxs.size} pending transactions...`);
                // Wait up to 30 seconds for pending txs
                let waitTime = 0;
                while (this.pendingTxs.size > 0 && waitTime < 30000) {
                    await new Promise(resolve => setTimeout(resolve, 1000));
                    waitTime += 1000;
                }
            }

            this.logger.info("✅ Graceful shutdown completed");
            process.exit(0);
        };

        process.on('SIGINT', () => shutdown('SIGINT'));
        process.on('SIGTERM', () => shutdown('SIGTERM'));
    }
}

// Start the production keeper
if (require.main === module) {
    const keeper = new ProductionKeeperSSE({
        contractAddress: process.env.CONTRACT_ADDRESS,
        debounceMs: process.env.DEBOUNCE_MS,
        minPriceChangePercent: process.env.MIN_PRICE_CHANGE_PERCENT
    });

    keeper.start().catch((error) => {
        console.error("Failed to start keeper:", error);
        process.exit(1);
    });
}

module.exports = ProductionKeeperSSE;