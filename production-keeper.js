const { ethers } = require("ethers");
const https = require("https");

/**
 * @title ProductionKeeper
 * @notice Production-ready keeper with robust nonce management and high-frequency capabilities
 */
class ProductionKeeper {
    constructor(config = {}) {
        this.provider = new ethers.JsonRpcProvider(config.rpcUrl || "https://subnets.avax.network/eto/testnet/rpc");
        this.wallet = new ethers.Wallet(process.env.PRIVATE_KEY, this.provider);
        
        // Nonce management - track pending transactions
        this.currentNonce = 0;
        this.pendingTransactions = new Map(); // nonce -> tx hash
        this.lastNonceUpdate = 0;
        
        // Transaction pool - simpler approach
        this.pendingUpdate = null;
        this.isProcessing = false;
        
        // Performance tracking
        this.metrics = {
            totalUpdates: 0,
            successfulUpdates: 0,
            failedUpdates: 0,
            averageLatency: 0
        };
        
        // Contract setup
        this.consumerContract = new ethers.Contract(
            config.contractAddress || "0x36df4CF7cB10eD741Ed6EC553365cf515bc07121",
            [
                "function updatePriceFeeds(bytes32[] calldata feedIds, int64[] calldata prices, uint256[] calldata timestamps) external",
                "function getValidFeedCount() external view returns (uint256 count)",
                "function viewPrice() external view returns (uint256 price, uint256 timestamp)",
                "function isStale() external view returns (bool isStale)"
            ],
            this.wallet
        );

        // MAANG feeds
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

        this.hermesUrl = "https://hermes.pyth.network/v2/updates/price/latest";
    }

    async start() {
        console.log("🚀 Starting Production Keeper...");
        
        // Initialize nonce
        await this.refreshNonce();
        
        // Start price polling
        this.startPricePolling();
        
        // Start health monitoring
        this.startHealthMonitoring();
        
        console.log("✅ Production Keeper started successfully");
    }

    async refreshNonce() {
        try {
            // Get the actual nonce from the blockchain
            const nonce = await this.provider.getTransactionCount(this.wallet.address, 'pending');
            this.currentNonce = nonce;
            this.lastNonceUpdate = Date.now();
            console.log(`📊 Nonce refreshed: ${nonce}`);
        } catch (error) {
            console.error("❌ Failed to refresh nonce:", error.message);
        }
    }

    async getNextNonce() {
        // Always refresh nonce before getting next one
        await this.refreshNonce();
        return this.currentNonce;
    }

    async fetchLatestPrices() {
        return new Promise((resolve, reject) => {
            const priceIdsQuery = this.priceIds.map(id => `ids[]=${id.replace('0x', '')}`).join('&');
            const url = `${this.hermesUrl}?${priceIdsQuery}`;

            https.get(url, (res) => {
                let data = '';
                res.on('data', (chunk) => data += chunk);
                res.on('end', () => {
                    try {
                        resolve(JSON.parse(data));
                    } catch (error) {
                        reject(error);
                    }
                });
            }).on('error', reject);
        });
    }

    async processPriceUpdate(data) {
        if (!data.parsed || data.parsed.length === 0) {
            console.log("📊 No price updates available");
            return;
        }

        const currentTimestamp = Math.floor(Date.now() / 1000);
        const feedIds = [];
        const prices = [];
        const timestamps = [];

        for (const feed of data.parsed) {
            const feedId = `0x${feed.id}`;
            const rawPrice = feed.price.price;
            const expo = feed.price.expo;
            
            // Calculate actual price using expo: price * 10^expo
            const actualPrice = Math.round(rawPrice * Math.pow(10, expo));
            // Convert to 8 decimal format for contract
            const price = Math.round(actualPrice * 1e8);
            
            feedIds.push(feedId);
            prices.push(price);
            timestamps.push(currentTimestamp);

            const symbol = this.symbols[feedId] || "UNKNOWN";
            const priceUSD = (actualPrice).toFixed(2);
            console.log(`📈 ${symbol}: $${priceUSD}`);
        }

        // Store the update data
        this.pendingUpdate = {
            feedIds,
            prices,
            timestamps,
            timestamp: Date.now()
        };
    }

    async submitTransaction(txData) {
        const startTime = Date.now();
        
        try {
            const nonce = await this.getNextNonce();
            const gasPrice = await this.getOptimalGasPrice();
            
            const tx = await this.wallet.sendTransaction({
                ...txData,
                nonce: nonce,
                gasPrice: gasPrice,
                gasLimit: 500000
            });

            // Track this transaction
            this.pendingTransactions.set(nonce, tx.hash);
            
            this.metrics.totalUpdates++;
            this.metrics.successfulUpdates++;
            this.metrics.averageLatency = (this.metrics.averageLatency + (Date.now() - startTime)) / 2;

            console.log(`✅ Transaction submitted: ${tx.hash}`);
            
            // Wait for confirmation before proceeding
            await tx.wait(1);
            this.pendingTransactions.delete(nonce);
            
            return tx;
            
        } catch (error) {
            this.metrics.totalUpdates++;
            this.metrics.failedUpdates++;
            
            console.error(`❌ Transaction failed: ${error.message}`);
            throw error;
        }
    }

    async getOptimalGasPrice() {
        try {
            const feeData = await this.provider.getFeeData();
            // Use 120% of base fee for faster confirmation
            return Math.floor(feeData.gasPrice * 1.2);
        } catch (error) {
            // Fallback gas price
            return ethers.parseUnits("30", "gwei");
        }
    }

    async processUpdate() {
        if (!this.pendingUpdate || this.isProcessing) return;

        this.isProcessing = true;
        const updateData = this.pendingUpdate;
        this.pendingUpdate = null; // Clear it immediately

        try {
            await this.submitTransaction({
                to: this.consumerContract.target,
                data: this.consumerContract.interface.encodeFunctionData("updatePriceFeeds", [
                    updateData.feedIds,
                    updateData.prices,
                    updateData.timestamps
                ])
            });
            
            console.log(`📊 Update processed successfully`);
            
        } catch (error) {
            console.error(`❌ Update processing failed: ${error.message}`);
            // Don't re-queue failed updates to avoid infinite loops
        } finally {
            this.isProcessing = false;
        }
    }

    startPricePolling() {
        // Poll every 5 seconds - much slower to avoid nonce conflicts
        setInterval(async () => {
            if (!this.isProcessing && !this.pendingUpdate) {
                try {
                    this.isProcessing = true;
                    
                    // Fetch prices
                    const priceData = await this.fetchLatestPrices();
                    await this.processPriceUpdate(priceData);
                    
                    // Reset processing flag before calling processUpdate
                    this.isProcessing = false;
                    
                    // Process the update immediately
                    await this.processUpdate();
                    
                } catch (error) {
                    console.error("❌ Price polling error:", error.message);
                } finally {
                    this.isProcessing = false;
                }
            }
        }, 5000); // Poll every 5 seconds
    }

    startHealthMonitoring() {
        setInterval(async () => {
            try {
                const balance = await this.provider.getBalance(this.wallet.address);
                const validFeeds = await this.consumerContract.getValidFeedCount();
                const isStale = await this.consumerContract.isStale();
                
                console.log("🏥 Health Check:");
                console.log(`  💳 Balance: ${ethers.formatEther(balance)} AVAX`);
                console.log(`  📊 Valid Feeds: ${validFeeds}`);
                console.log(`  ⏰ Stale: ${isStale}`);
                console.log(`  📈 Success Rate: ${((this.metrics.successfulUpdates / this.metrics.totalUpdates) * 100).toFixed(1)}%`);
                console.log(`  ⚡ Avg Latency: ${this.metrics.averageLatency}ms`);
                
                // Refresh nonce every 60 seconds
                if (Date.now() - this.lastNonceUpdate > 60000) {
                    await this.refreshNonce();
                }
                
            } catch (error) {
                console.error("❌ Health check failed:", error.message);
            }
        }, 60000); // Every 60 seconds
    }
}

// Start the production keeper
const keeper = new ProductionKeeper({
    contractAddress: "0x36df4CF7cB10eD741Ed6EC553365cf515bc07121"
});

keeper.start().catch(console.error);

// Graceful shutdown
process.on('SIGINT', () => {
    console.log('\n🛑 Shutting down production keeper...');
    process.exit(0);
});
