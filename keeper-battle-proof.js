const { ethers } = require("ethers");
const EventSource = require("eventsource");

class BattleProofKeeper {
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
            "0x297cc1e1ee5fc2f45dff1dd11a46694567904f4dbc596c7cc216d6c688605a1b", // NVDA/USD
            "0xb43660a5f790c69354b0729a5ef9d50d68f1df92107540210b9cccba1f947cc2", // AMZN/USD
            "0x5b1703d7eb9dc8662a61556a2ca2f9861747c3fc803e01ba5a8ce35cb50a13a1"  // GOOGL/USD
        ];

        this.updateQueue = new Map();
        this.isProcessing = false;
        this.consecutiveErrors = 0;
        this.maxRetries = 5;
        this.baseDelay = 1000;
        this.maxDelay = 30000;

        this.setupSSEConnection();
        this.startBatchProcessor();
    }

    setupSSEConnection() {
        const priceIdsQuery = this.priceIds.map(id => `ids[]=${id}`).join('&');
        const sseUrl = `https://hermes.pyth.network/v2/updates/price/stream?${priceIdsQuery}&parsed=true&allow_unordered=true`;

        console.log("🚀 Connecting to Hermes SSE stream...");
        this.eventSource = new EventSource(sseUrl);

        this.eventSource.onopen = () => {
            console.log("✅ SSE connection established");
            this.consecutiveErrors = 0;
        };

        this.eventSource.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                this.handlePriceUpdate(data);
            } catch (error) {
                console.error("❌ Error parsing SSE message:", error);
            }
        };

        this.eventSource.onerror = (error) => {
            console.error("❌ SSE connection error:", error);
            this.consecutiveErrors++;
            this.reconnectWithBackoff();
        };
    }

    handlePriceUpdate(data) {
        if (data.parsed && data.parsed.length > 0) {
            for (const price of data.parsed) {
                const priceId = `0x${price.id}`;
                if (this.priceIds.includes(priceId)) {
                    console.log(`📈 Price update for ${priceId}: $${(price.price.price * Math.pow(10, price.price.expo)).toFixed(2)}`);

                    // Queue update with VAA data
                    this.updateQueue.set(priceId, {
                        vaa: data.binary.data[0], // Get the VAA bytes
                        timestamp: Date.now(),
                        price: price.price.price,
                        expo: price.price.expo
                    });
                }
            }
        }
    }

    async startBatchProcessor() {
        setInterval(async () => {
            if (this.updateQueue.size > 0 && !this.isProcessing) {
                await this.processBatch();
            }
        }, 2000); // Process every 2 seconds for instant updates
    }

    async processBatch() {
        if (this.isProcessing) return;

        this.isProcessing = true;
        const updates = Array.from(this.updateQueue.values()).map(update => update.vaa);
        this.updateQueue.clear();

        if (updates.length === 0) {
            this.isProcessing = false;
            return;
        }

        console.log(`🔄 Processing batch of ${updates.length} updates...`);

        try {
            // Convert hex strings to bytes
            const updateData = updates.map(update =>
                update.startsWith('0x') ? update : `0x${update}`
            );

            // Get update fee
            const fee = await this.pythContract.getUpdateFee(updateData);
            console.log(`💰 Update fee: ${ethers.formatEther(fee)} AVAX`);

            // Submit update with retry logic
            const tx = await this.submitWithRetry(updateData, fee);
            console.log(`✅ Batch submitted! Tx: ${tx.hash}`);

            // Wait for confirmation
            const receipt = await tx.wait();
            console.log(`🎯 Confirmed in block ${receipt.blockNumber}`);

            this.consecutiveErrors = 0;

        } catch (error) {
            console.error("❌ Batch processing failed:", error);
            this.consecutiveErrors++;

            // Re-queue updates if they're recent (within 30 seconds)
            const now = Date.now();
            updates.forEach((update, index) => {
                if (now - update.timestamp < 30000) {
                    this.updateQueue.set(`retry_${index}`, update);
                }
            });
        }

        this.isProcessing = false;
    }

    async submitWithRetry(updateData, fee, attempt = 1) {
        try {
            const gasPrice = await this.provider.getFeeData();

            const tx = await this.pythContract.updatePriceFeeds(updateData, {
                value: fee,
                gasLimit: 300000 + (updateData.length * 50000),
                gasPrice: gasPrice.gasPrice * BigInt(120) / BigInt(100) // 20% premium for speed
            });

            return tx;

        } catch (error) {
            if (attempt < this.maxRetries) {
                const delay = Math.min(this.baseDelay * Math.pow(2, attempt - 1), this.maxDelay);
                console.log(`⏳ Retry ${attempt}/${this.maxRetries} in ${delay}ms...`);

                await new Promise(resolve => setTimeout(resolve, delay));
                return this.submitWithRetry(updateData, fee, attempt + 1);
            }
            throw error;
        }
    }

    reconnectWithBackoff() {
        if (this.eventSource) {
            this.eventSource.close();
        }

        const delay = Math.min(this.baseDelay * Math.pow(2, this.consecutiveErrors), this.maxDelay);
        console.log(`🔄 Reconnecting in ${delay}ms... (attempt ${this.consecutiveErrors + 1})`);

        setTimeout(() => {
            this.setupSSEConnection();
        }, delay);
    }

    async healthCheck() {
        try {
            const balance = await this.wallet.getBalance();
            const balanceETH = ethers.formatEther(balance);

            console.log(`💳 Keeper balance: ${balanceETH} AVAX`);

            if (parseFloat(balanceETH) < 0.1) {
                console.warn("⚠️  Low balance warning! Please fund keeper wallet");
            }

            // Test contract connectivity
            const fee = await this.pythContract.getUpdateFee([]);
            console.log("🏥 Health check passed - contract accessible");

        } catch (error) {
            console.error("❌ Health check failed:", error);
        }
    }

    start() {
        console.log("🚀 BattleProof Keeper starting...");
        this.healthCheck();

        // Run health checks every 5 minutes
        setInterval(() => this.healthCheck(), 5 * 60 * 1000);

        // Graceful shutdown
        process.on('SIGINT', () => {
            console.log("\n🛑 Shutting down keeper...");
            if (this.eventSource) {
                this.eventSource.close();
            }
            process.exit(0);
        });
    }
}

// Create and start keeper
const keeper = new BattleProofKeeper();
keeper.start();