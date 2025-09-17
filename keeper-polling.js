const { ethers } = require("ethers");
const https = require("https");

class BattleProofKeeperPolling {
    constructor() {
        this.provider = new ethers.JsonRpcProvider("https://subnets.avax.network/eto/testnet/rpc");
        this.wallet = new ethers.Wallet(process.env.PRIVATE_KEY || "0x75de5e9a6ee5b863f3aa44ea9b3b6f17c69c8b74c8c3cdab74e67cc4ad8e26c0", this.provider);

        this.pythContract = new ethers.Contract(
            "0x431904FE789A377d166eEFbaE1681239C17B134b",
            [
                "function updatePriceFeeds(bytes[] calldata updateData) external payable",
                "function getUpdateFee(bytes[] calldata updateData) external view returns (uint256)"
            ],
            this.wallet
        );

        this.priceIds = [
            "0x78a3e3b8e676a8f73c439f5d749737034b139bbbe899ba5775216fba596607fe", // META/USD
            "0x49f6b65cb1de6b10eaf75e7c03ca029c306d0357e91b5311b175084a5ad55688", // AAPL/USD
            "0xb5d0e0fa58a1f8b81498ae670ce93c872d14434b72c364885d4fa1b257cbb07a", // AMZN/USD (corrected)
            "0xe65ff435be42630439c96396653a342829e877e2aafaeaf1a10d0ee5fd2cf3f2"  // GOOG/USD (working feed)
        ];

        this.maxRetries = 5;
        this.baseDelay = 1000;
        this.lastPrices = new Map();

        this.startPolling();
    }

    async fetchLatestPrices() {
        return new Promise((resolve, reject) => {
            const priceIdsQuery = this.priceIds.map(id => `ids[]=${id.replace('0x', '')}`).join('&');
            const url = `https://hermes.pyth.network/v2/updates/price/latest?${priceIdsQuery}`;

            const req = https.get(url, (res) => {
                let data = '';
                res.on('data', chunk => data += chunk);
                res.on('end', () => {
                    try {
                        const result = JSON.parse(data);
                        resolve(result);
                    } catch (error) {
                        reject(error);
                    }
                });
            });

            req.on('error', reject);
            req.setTimeout(10000, () => {
                req.destroy();
                reject(new Error('Request timeout'));
            });
        });
    }

    async startPolling() {
        console.log("🚀 Starting battle-proof polling keeper...");

        // Poll every 5 seconds for instant updates
        setInterval(async () => {
            try {
                const priceData = await this.fetchLatestPrices();
                await this.processPriceUpdate(priceData);
            } catch (error) {
                console.error("❌ Polling error:", error.message);
            }
        }, 5000);

        // Health check every minute
        setInterval(() => this.healthCheck(), 60000);

        // Initial health check
        await this.healthCheck();
    }

    async processPriceUpdate(data) {
        if (!data.binary || !data.binary.data || data.binary.data.length === 0) {
            console.log("⏭️  No price updates available");
            return;
        }

        console.log(`📊 Processing ${data.binary.data.length} price updates...`);

        try {
            const updateData = data.binary.data.map(vaa => `0x${vaa}`);

            // Get update fee
            const fee = await this.pythContract.getUpdateFee(updateData);
            console.log(`💰 Update fee: ${ethers.formatEther(fee)} AVAX`);

            // Submit with retry logic
            const tx = await this.submitWithRetry(updateData, fee);
            console.log(`✅ Updates submitted! Tx: ${tx.hash}`);

            // Wait for confirmation
            const receipt = await tx.wait();
            console.log(`🎯 Confirmed in block ${receipt.blockNumber}`);

            // Log price changes
            if (data.parsed) {
                for (const price of data.parsed) {
                    const symbol = this.getSymbol(price.id);
                    const currentPrice = price.price.price * Math.pow(10, price.price.expo);
                    const lastPrice = this.lastPrices.get(price.id);

                    if (lastPrice && lastPrice !== currentPrice) {
                        const change = ((currentPrice - lastPrice) / lastPrice * 100).toFixed(2);
                        console.log(`📈 ${symbol}: $${this.formatPrice(currentPrice)} (${change > 0 ? '+' : ''}${change}%)`);
                    } else if (!lastPrice) {
                        console.log(`📈 ${symbol}: $${this.formatPrice(currentPrice)} (initial)`);
                    }

                    this.lastPrices.set(price.id, currentPrice);
                }
            }

        } catch (error) {
            console.error("❌ Update submission failed:", error.message);
        }
    }

    getSymbol(id) {
        const symbols = {
            '78a3e3b8e676a8f73c439f5d749737034b139bbbe899ba5775216fba596607fe': 'META',
            '49f6b65cb1de6b10eaf75e7c03ca029c306d0357e91b5311b175084a5ad55688': 'AAPL',
            'b5d0e0fa58a1f8b81498ae670ce93c872d14434b72c364885d4fa1b257cbb07a': 'AMZN',
            'e65ff435be42630439c96396653a342829e877e2aafaeaf1a10d0ee5fd2cf3f2': 'GOOG'
        };
        return symbols[id] || id.slice(0, 8);
    }

    formatPrice(price) {
        if (price >= 1000) {
            return price.toFixed(0);
        } else if (price >= 100) {
            return price.toFixed(2);
        } else if (price >= 10) {
            return price.toFixed(3);
        } else {
            return price.toFixed(4);
        }
    }

    async submitWithRetry(updateData, fee, attempt = 1) {
        try {
            const feeData = await this.provider.getFeeData();

            const tx = await this.pythContract.updatePriceFeeds(updateData, {
                value: fee,
                gasLimit: 300000 + (updateData.length * 50000),
                gasPrice: feeData.gasPrice ? feeData.gasPrice * BigInt(120) / BigInt(100) : undefined
            });

            return tx;

        } catch (error) {
            if (attempt < this.maxRetries && !error.message.includes("insufficient funds")) {
                const delay = this.baseDelay * Math.pow(2, attempt - 1);
                console.log(`⏳ Retry ${attempt}/${this.maxRetries} in ${delay}ms...`);

                await new Promise(resolve => setTimeout(resolve, delay));
                return this.submitWithRetry(updateData, fee, attempt + 1);
            }
            throw error;
        }
    }

    async healthCheck() {
        try {
            const balance = await this.provider.getBalance(this.wallet.address);
            const balanceETH = ethers.formatEther(balance);

            console.log(`💳 Keeper balance: ${balanceETH} AVAX`);

            if (parseFloat(balanceETH) < 0.1) {
                console.warn("⚠️  Low balance warning! Please fund keeper wallet");
            }

            // Test contract connectivity
            const fee = await this.pythContract.getUpdateFee([]);
            console.log("🏥 Health check passed - contract accessible");

        } catch (error) {
            console.error("❌ Health check failed:", error.message);
        }
    }

    start() {
        console.log("🚀 BattleProof Polling Keeper starting...");

        // Graceful shutdown
        process.on('SIGINT', () => {
            console.log("\n🛑 Shutting down keeper...");
            process.exit(0);
        });
    }
}

// Create and start keeper
const keeper = new BattleProofKeeperPolling();
keeper.start();