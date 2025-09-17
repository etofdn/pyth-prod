#!/usr/bin/env node

const { ethers } = require('ethers');
require('dotenv').config();

// Contract addresses
const PYTH_PRICE_CONSUMER_ADDRESS = '0xBbc5ED6A9c8B9f8C4dC2ccd3fd06b9542eF7a02A';

// Price feed IDs (mix of crypto and equity for testing)
const PRICE_FEEDS = {
    // Crypto assets (these should work 24/7)
    'BTC/USD': '0xe62df6c8b4a85fe1a67db44dc12de5db330f7ac66b72dc658afedf0f4a415b43',
    'ETH/USD': '0xff61491a931112ddf1bd8147cd1b641375f79f5825126d665480874634fd0ace',

    // Equity assets (market hours dependent)
    'META/USD': '0x78a3e3b8e676a8f73c439f5d749737034b139bbbe899ba5775216fba596607fe',
    'AAPL/USD': '0x49f6b65cb1de6b10eaf75e7c03ca029c306d0357e91b5311b175084a5ad55688',
    'NVDA/USD': '0xb1073854ed24cbc755dc527418f52b7d271f6cc967bbf8d8129112b18860a593'
};

// ABI for PythPriceConsumer
const PRICE_CONSUMER_ABI = [
    "function updatePriceFeeds(bytes[] calldata updateData) external payable",
    "function getLatestPrice(bytes32 priceId) external view returns (int64, uint256)",
    "function getUpdateFee(bytes[] calldata updateData) external view returns (uint256)"
];

async function fetchPriceUpdates(priceIds) {
    try {
        // Remove 0x prefix from price IDs for API
        const cleanIds = priceIds.map(id => id.startsWith('0x') ? id.slice(2) : id);
        const idsParams = cleanIds.map(id => `ids[]=${id}`).join('&');
        const url = `https://hermes.pyth.network/v2/updates/price/latest?${idsParams}&encoding=hex`;

        console.log('Fetching price updates from Hermes...');
        console.log('URL:', url);

        const response = await fetch(url);
        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`HTTP error! status: ${response.status} - ${response.statusText}\nResponse: ${errorText}`);
        }

        const data = await response.json();
        console.log('Hermes response received');
        console.log('Response structure:', Object.keys(data));

        if (data.binary && data.binary.data) {
            console.log('Binary data length:', data.binary.data.length);

            // Convert hex strings to bytes for the contract
            const updateData = data.binary.data.map(hexString => {
                // Ensure proper hex formatting
                const cleanHex = hexString.startsWith('0x') ? hexString.slice(2) : hexString;
                return '0x' + cleanHex;
            });

            console.log(`Processed ${updateData.length} price updates`);
            return updateData;
        } else {
            console.log('No binary data found in response');
            console.log('Full response:', JSON.stringify(data, null, 2));
            return [];
        }
    } catch (error) {
        console.error('Error fetching price updates:', error);
        return [];
    }
}

async function updateAndReadPrices() {
    try {
        // Setup provider and signer
        const provider = new ethers.JsonRpcProvider(process.env.RPC_URL);
        const signer = new ethers.Wallet(process.env.PRIVATE_KEY, provider);

        console.log('Connected to ETO Testnet');
        console.log('Signer address:', await signer.getAddress());

        // Connect to contract
        const priceConsumer = new ethers.Contract(
            PYTH_PRICE_CONSUMER_ADDRESS,
            PRICE_CONSUMER_ABI,
            signer
        );

        // Get price feed IDs
        const priceIds = Object.values(PRICE_FEEDS);
        console.log('Price feed IDs:', priceIds);

        // Fetch price updates from Hermes
        const updateData = await fetchPriceUpdates(priceIds);

        if (updateData.length === 0) {
            console.log('No update data received. Testing with mock data...');

            // Test reading current prices without update
            console.log('\n=== Current Prices (may be stale) ===');
            for (const [symbol, priceId] of Object.entries(PRICE_FEEDS)) {
                try {
                    const [price, timestamp] = await priceConsumer.getLatestPrice(priceId);
                    console.log(`${symbol}: $${ethers.formatUnits(price, 8)} (timestamp: ${timestamp})`);
                } catch (error) {
                    console.log(`${symbol}: No data available`);
                }
            }
            return;
        }

        console.log(`\nReceived ${updateData.length} price updates`);

        // Get update fee
        const updateFee = await priceConsumer.getUpdateFee(updateData);
        console.log('Update fee:', ethers.formatEther(updateFee), 'ETH');

        // Check balance
        const balance = await provider.getBalance(await signer.getAddress());
        console.log('Account balance:', ethers.formatEther(balance), 'ETH');

        if (balance < updateFee) {
            console.error('Insufficient balance for update fee');
            return;
        }

        // Update price feeds
        console.log('\nUpdating price feeds...');
        const tx = await priceConsumer.updatePriceFeeds(updateData, {
            value: updateFee,
            gasLimit: 500000
        });

        console.log('Transaction hash:', tx.hash);
        await tx.wait();
        console.log('Price feeds updated successfully!');

        // Read updated prices
        console.log('\n=== Updated Prices ===');
        for (const [symbol, priceId] of Object.entries(PRICE_FEEDS)) {
            try {
                const [price, timestamp] = await priceConsumer.getLatestPrice(priceId);
                const formattedPrice = ethers.formatUnits(price, 8);
                const date = new Date(Number(timestamp) * 1000);
                console.log(`${symbol}: $${formattedPrice} (${date.toISOString()})`);
            } catch (error) {
                console.log(`${symbol}: Error reading price - ${error.message}`);
            }
        }

    } catch (error) {
        console.error('Error:', error);
    }
}

// Run if called directly
if (require.main === module) {
    updateAndReadPrices();
}

module.exports = { updateAndReadPrices, fetchPriceUpdates };