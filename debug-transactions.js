#!/usr/bin/env node

const { ethers } = require('ethers');
require('dotenv').config();

// Contract addresses
const PYTH_PRICE_CONSUMER_ADDRESS = '0xBbc5ED6A9c8B9f8C4dC2ccd3fd06b9542eF7a02A';

// Test with just crypto feeds first (they should always be available)
const CRYPTO_FEEDS = {
    'BTC/USD': '0xe62df6c8b4a85fe1a67db44dc12de5db330f7ac66b72dc658afedf0f4a415b43',
    'ETH/USD': '0xff61491a931112ddf1bd8147cd1b641375f79f5825126d665480874634fd0ace'
};

// Full ABI for debugging
const PRICE_CONSUMER_ABI = [
    "function updatePriceFeeds(bytes[] calldata updateData) external payable",
    "function getLatestPrice(bytes32 priceId) external view returns (int64, uint256)",
    "function getUpdateFee(bytes[] calldata updateData) external view returns (uint256)",
    "function pyth() external view returns (address)"
];

async function fetchSinglePriceUpdate(priceId) {
    try {
        const cleanId = priceId.startsWith('0x') ? priceId.slice(2) : priceId;
        const url = `https://hermes.pyth.network/v2/updates/price/latest?ids[]=${cleanId}&encoding=hex`;

        console.log(`Fetching single price update for ${priceId}...`);
        const response = await fetch(url);

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`HTTP ${response.status}: ${errorText}`);
        }

        const data = await response.json();
        console.log('Single price response:', {
            hasBinary: !!data.binary,
            hasData: !!data.binary?.data,
            dataLength: data.binary?.data?.length || 0,
            parsed: data.parsed?.length || 0
        });

        if (data.binary?.data?.length > 0) {
            const updateData = data.binary.data.map(hex => '0x' + (hex.startsWith('0x') ? hex.slice(2) : hex));
            return updateData;
        }
        return [];
    } catch (error) {
        console.error(`Error fetching ${priceId}:`, error.message);
        return [];
    }
}

async function testMockPythDirectly() {
    try {
        const provider = new ethers.JsonRpcProvider(process.env.RPC_URL);
        const signer = new ethers.Wallet(process.env.PRIVATE_KEY, provider);

        console.log('=== Testing Mock Pyth Directly ===');
        console.log('Signer:', await signer.getAddress());
        console.log('Balance:', ethers.formatEther(await provider.getBalance(await signer.getAddress())), 'ETH');

        const priceConsumer = new ethers.Contract(PYTH_PRICE_CONSUMER_ADDRESS, PRICE_CONSUMER_ABI, signer);

        // Get the underlying Pyth contract address
        const pythAddress = await priceConsumer.pyth();
        console.log('Pyth contract address:', pythAddress);

        // Test with BTC first
        const btcPriceId = CRYPTO_FEEDS['BTC/USD'];
        console.log(`\n=== Testing BTC Price Update (${btcPriceId}) ===`);

        // Fetch update data
        const updateData = await fetchSinglePriceUpdate(btcPriceId);
        if (updateData.length === 0) {
            console.log('No update data available for BTC');
            return;
        }

        console.log('Update data received:', updateData.length, 'entries');
        console.log('First update data length:', updateData[0].length);

        // Get update fee
        try {
            const updateFee = await priceConsumer.getUpdateFee(updateData);
            console.log('Update fee:', ethers.formatEther(updateFee), 'ETH');

            // Try to call updatePriceFeeds with proper gas estimation
            console.log('\n=== Attempting Price Update ===');

            // Estimate gas first
            let gasEstimate;
            try {
                gasEstimate = await priceConsumer.updatePriceFeeds.estimateGas(updateData, { value: updateFee });
                console.log('Gas estimate:', gasEstimate.toString());
            } catch (gasError) {
                console.error('Gas estimation failed:', gasError.message);
                console.log('Trying with higher gas limit...');
                gasEstimate = 1000000n; // 1M gas
            }

            // Try the actual transaction
            const tx = await priceConsumer.updatePriceFeeds(updateData, {
                value: updateFee,
                gasLimit: gasEstimate + 100000n // Add buffer
            });

            console.log('Transaction sent:', tx.hash);
            const receipt = await tx.wait();
            console.log('Transaction successful!');
            console.log('Gas used:', receipt.gasUsed.toString());

            // Try to read the price
            console.log('\n=== Reading Updated Price ===');
            try {
                const [price, timestamp] = await priceConsumer.getLatestPrice(btcPriceId);
                console.log('BTC Price:', ethers.formatUnits(price, 8), 'USD');
                console.log('Timestamp:', new Date(Number(timestamp) * 1000).toISOString());
            } catch (readError) {
                console.error('Error reading price:', readError.message);
            }

        } catch (feeError) {
            console.error('Error getting update fee:', feeError.message);
        }

    } catch (error) {
        console.error('Test failed:', error);
    }
}

async function debugContractState() {
    try {
        const provider = new ethers.JsonRpcProvider(process.env.RPC_URL);
        const priceConsumer = new ethers.Contract(PYTH_PRICE_CONSUMER_ADDRESS, PRICE_CONSUMER_ABI, provider);

        console.log('=== Contract State Debug ===');

        // Check if contract exists
        const code = await provider.getCode(PYTH_PRICE_CONSUMER_ADDRESS);
        console.log('Contract has code:', code !== '0x');

        if (code === '0x') {
            console.error('Contract not found at address!');
            return;
        }

        // Get Pyth address
        try {
            const pythAddress = await priceConsumer.pyth();
            console.log('Pyth contract:', pythAddress);

            const pythCode = await provider.getCode(pythAddress);
            console.log('Pyth contract has code:', pythCode !== '0x');
        } catch (error) {
            console.error('Error getting Pyth address:', error.message);
        }

    } catch (error) {
        console.error('Debug failed:', error);
    }
}

// Run diagnostics
async function main() {
    console.log('Starting transaction failure diagnosis...\n');

    await debugContractState();
    console.log('\n' + '='.repeat(50) + '\n');
    await testMockPythDirectly();
}

if (require.main === module) {
    main();
}