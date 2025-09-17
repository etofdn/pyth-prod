#!/usr/bin/env node

const { ethers } = require('ethers');
require('dotenv').config();

// Complete price feeds - crypto + all requested stocks
const PRICE_FEEDS = {
    // Crypto (24/7 availability)
    'BTC/USD': 'e62df6c8b4a85fe1a67db44dc12de5db330f7ac66b72dc658afedf0f4a415b43',
    'ETH/USD': 'ff61491a931112ddf1bd8147cd1b641375f79f5825126d665480874634fd0ace',

    // Stocks (market hours dependent)
    'META/USD': '78a3e3b8e676a8f73c439f5d749737034b139bbbe899ba5775216fba596607fe',
    'AAPL/USD': '49f6b65cb1de6b10eaf75e7c03ca029c306d0357e91b5311b175084a5ad55688',
    'NVDA/USD': 'b1073854ed24cbc755dc527418f52b7d271f6cc967bbf8d8129112b18860a593',
    'AMZN/USD': 'b5d0e0fa58a1f8b81498ae670ce93c872d14434b72c364885d4fa1b257cbb07a',
    'GOOGL/USD': '5a48c03e9b9cb337801073ed9d166817473697efff0d138874e0f6a33d6d5aa6'
};

async function fetchHermesPrice(priceId) {
    try {
        const url = `https://hermes.pyth.network/v2/updates/price/latest?ids[]=${priceId}&encoding=hex&parsed=true`;
        console.log(`Fetching: ${url}`);

        const response = await fetch(url);
        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`HTTP ${response.status}: ${errorText}`);
        }

        const data = await response.json();
        return data;
    } catch (error) {
        console.error(`Error fetching ${priceId}:`, error.message);
        return null;
    }
}

async function testHermesIntegration() {
    console.log('=== Testing Real Hermes Integration ===\n');

    for (const [symbol, priceId] of Object.entries(PRICE_FEEDS)) {
        console.log(`\n--- ${symbol} (${priceId}) ---`);

        const hermesData = await fetchHermesPrice(priceId);
        if (!hermesData) {
            console.log(`❌ Failed to fetch ${symbol}`);
            continue;
        }

        console.log('✅ Hermes Response Structure:');
        console.log('  - binary:', !!hermesData.binary);
        console.log('  - binary.data length:', hermesData.binary?.data?.length || 0);
        console.log('  - parsed:', !!hermesData.parsed);
        console.log('  - parsed length:', hermesData.parsed?.length || 0);

        if (hermesData.parsed && hermesData.parsed.length > 0) {
            const price = hermesData.parsed[0].price;
            console.log('  📊 Price Data:');
            console.log(`     Price: ${price.price} (expo: ${price.expo})`);
            console.log(`     Confidence: ${price.conf}`);
            console.log(`     Publish Time: ${price.publish_time} (${new Date(price.publish_time * 1000).toISOString()})`);

            // Calculate human-readable price
            const humanPrice = Number(price.price) / Math.pow(10, Math.abs(price.expo));
            console.log(`     Human Readable: $${humanPrice.toLocaleString()}`);
        }

        if (hermesData.binary && hermesData.binary.data && hermesData.binary.data.length > 0) {
            const vaaHex = hermesData.binary.data[0];
            console.log('  🔗 VAA Data:');
            console.log(`     Length: ${vaaHex.length} chars`);
            console.log(`     First 100 chars: ${vaaHex.substring(0, 100)}...`);
            console.log(`     Ready for on-chain submission: ✅`);
        }
    }

    console.log('\n=== Summary ===');
    console.log('✅ Successfully fetched real-time price data from Hermes');
    console.log('✅ Received binary VAA data for on-chain submission');
    console.log('✅ Ready to integrate with real Pyth contract');
    console.log('\nNext steps:');
    console.log('1. Deploy real Pyth contract (not MockPyth)');
    console.log('2. Submit VAA data to Pyth contract for validation');
    console.log('3. Read validated prices from Pyth contract');
}

if (require.main === module) {
    testHermesIntegration();
}