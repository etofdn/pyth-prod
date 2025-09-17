#!/usr/bin/env node

const { ethers } = require('ethers');
require('dotenv').config();

// Contract addresses
const PYTH_PRICE_CONSUMER_ADDRESS = '0xBbc5ED6A9c8B9f8C4dC2ccd3fd06b9542eF7a02A';

// MockPyth ABI (has additional functions for setting prices)
const MOCK_PYTH_ABI = [
    "function updatePriceFeeds(bytes[] calldata updateData) external payable",
    "function updatePriceFeedsIfNecessary(bytes[] calldata updateData, bytes32[] calldata priceIds, uint64[] calldata publishTimes) external payable",
    "function createPriceFeedIfNotExists(bytes32 id, int64 price, uint64 conf, int32 expo, int64 emaPrice, uint64 emaConf, uint64 publishTime) external",
    "function updatePriceFromPythData(bytes calldata pythData) external payable",
    "function getPrice(bytes32 id) external view returns (PythStructs.Price memory price)",
    "function getPriceUnsafe(bytes32 id) external view returns (PythStructs.Price memory price)",
    "function getUpdateFee(bytes[] calldata updateData) external view returns (uint)",
    "function setPrice(bytes32 id, int64 price, uint64 conf, int32 expo, int64 emaPrice, uint64 emaConf, uint64 publishTime) external"
];

const PRICE_CONSUMER_ABI = [
    "function getLatestPrice(bytes32 priceId) external view returns (int64, uint256)",
    "function pyth() external view returns (address)"
];

// Price feeds with real-time Hermes data
const CRYPTO_FEEDS = {
    'BTC/USD': '0xe62df6c8b4a85fe1a67db44dc12de5db330f7ac66b72dc658afedf0f4a415b43',
    'ETH/USD': '0xff61491a931112ddf1bd8147cd1b641375f79f5825126d665480874634fd0ace'
};

async function fetchRealPrice(symbol, priceId) {
    try {
        const cleanId = priceId.startsWith('0x') ? priceId.slice(2) : priceId;
        const url = `https://hermes.pyth.network/v2/updates/price/latest?ids[]=${cleanId}&parsed=true`;

        const response = await fetch(url);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const data = await response.json();
        if (data.parsed && data.parsed.length > 0) {
            const priceData = data.parsed[0];
            console.log(`${symbol} real price data:`, {
                price: priceData.price?.price,
                conf: priceData.price?.conf,
                expo: priceData.price?.expo,
                publishTime: priceData.price?.publish_time
            });
            return priceData.price;
        }
        return null;
    } catch (error) {
        console.error(`Error fetching ${symbol}:`, error.message);
        return null;
    }
}

async function setMockPrices() {
    try {
        const provider = new ethers.JsonRpcProvider(process.env.RPC_URL);
        const signer = new ethers.Wallet(process.env.PRIVATE_KEY, provider);

        console.log('=== Setting Mock Prices with Real Hermes Data ===');
        console.log('Signer:', await signer.getAddress());

        const priceConsumer = new ethers.Contract(PYTH_PRICE_CONSUMER_ADDRESS, PRICE_CONSUMER_ABI, signer);
        const pythAddress = await priceConsumer.pyth();
        const mockPyth = new ethers.Contract(pythAddress, MOCK_PYTH_ABI, signer);

        console.log('MockPyth address:', pythAddress);

        // Fetch and set real prices
        for (const [symbol, priceId] of Object.entries(CRYPTO_FEEDS)) {
            console.log(`\n=== Processing ${symbol} ===`);

            const realPrice = await fetchRealPrice(symbol, priceId);
            if (!realPrice) {
                console.log(`Skipping ${symbol} - no real price data`);
                continue;
            }

            // Convert to MockPyth format
            const price = BigInt(realPrice.price || 0);
            const conf = BigInt(realPrice.conf || 1000000);
            const expo = realPrice.expo || -8;
            const emaPrice = price; // Use same as current price
            const emaConf = conf;
            const publishTime = BigInt(realPrice.publish_time || Math.floor(Date.now() / 1000));

            console.log(`Setting ${symbol} price:`, {
                price: price.toString(),
                conf: conf.toString(),
                expo,
                publishTime: publishTime.toString()
            });

            try {
                // Create or update the price feed
                const tx = await mockPyth.createPriceFeedIfNotExists(
                    priceId,
                    price,
                    conf,
                    expo,
                    emaPrice,
                    emaConf,
                    publishTime
                );

                console.log(`Transaction sent: ${tx.hash}`);
                await tx.wait();
                console.log(`${symbol} price set successfully!`);

                // Verify the price was set
                try {
                    const [storedPrice, timestamp] = await priceConsumer.getLatestPrice(priceId);
                    console.log(`Verification - ${symbol}:`, {
                        price: ethers.formatUnits(storedPrice, Math.abs(expo)),
                        timestamp: timestamp.toString()
                    });
                } catch (verifyError) {
                    console.error(`Error verifying ${symbol}:`, verifyError.message);
                }

            } catch (txError) {
                console.error(`Error setting ${symbol} price:`, txError.message);
            }
        }

        console.log('\n=== All Real Prices Set Successfully! ===');
        console.log('You can now read real-time crypto prices from your MockPyth contract');

    } catch (error) {
        console.error('Failed to set mock prices:', error);
    }
}

if (require.main === module) {
    setMockPrices();
}