const express = require('express');
const { ethers } = require('ethers');

const app = express();
const PORT = process.env.PORT || 3000;

// ETO Testnet configuration
const provider = new ethers.JsonRpcProvider(
    "https://testnet-eto-y246d.avax-test.network/ext/bc/2hpQwDpDGEa4915WnAp6MP7qCcoP35jqUHFji7p3o9E99UBJmk/rpc?token=da37bf16c0a88bb35f2e5c48bc8ce1229913fb135de21d7769a02b21f6c2b0ce"
);

// Contract addresses
const workingPythAddress = "0x431904FE789A377d166eEFbaE1681239C17B134b";
const maangOracleAddress = "0x7b0c3c7557897dd2bc9c9435100467942905411c";
// TODO: Update this with actual OracleAggregator address after deployment
const aggregatorAddress = "0x0000000000000000000000000000000000000000"; // PLACEHOLDER

// Contract ABIs
const workingPythABI = [
    "function getLatestPrice(bytes32 id) external view returns (int64 price, uint256 timestamp)",
    "function priceFeedExists(bytes32 id) external view returns (bool)"
];

const maangOracleABI = [
    "function viewPrice() external view returns (uint256 price, uint256 timestamp)",
    "function isStale() external view returns (bool)",
    "function getAssetName() external pure returns (string memory)",
    "function getMAANGBreakdown() external view returns (bytes32[] memory feedIds, uint256[] memory prices, uint256[] memory timestamps, bool[] memory isValid)"
];

const aggregatorABI = [
    "function getAggregatedPrice() external view returns (uint256 price, uint256 timestamp)",
    "function getAggregatedPriceWithFlags() external view returns (uint256 price, uint256 timestamp, uint8 flags)",
    "function canUpdate() external view returns (bool valid, uint8 reasonCode)",
    "function canUpdateWithReason() external view returns (bool valid, string memory reason)",
    "function getActiveOracleCount() external view returns (uint256)",
    "function getOracles() external view returns (address[] memory)",
    "function isOracleActive(address oracle) external view returns (bool)",
    "function updatePrice() external"
];

const workingPyth = new ethers.Contract(workingPythAddress, workingPythABI, provider);
const maangOracle = new ethers.Contract(maangOracleAddress, maangOracleABI, provider);
const aggregator = new ethers.Contract(aggregatorAddress, aggregatorABI, provider);

// MAANG feed IDs
const maangFeeds = {
    '78a3e3b8e676a8f73c439f5d749737034b139bbbe899ba5775216fba596607fe': 'META',
    '49f6b65cb1de6b10eaf75e7c03ca029c306d0357e91b5311b175084a5ad55688': 'AAPL',
    'b5d0e0fa58a1f8b81498ae670ce93c872d14434b72c364885d4fa1b257cbb07a': 'AMZN',
    'b1073854ed24cbc755dc527418f52b7d271f6cc967bbf8d8129112b18860a593': 'NVDA',
    '5a48c03e9b9cb337801073ed9d166817473697efff0d138874e0f6a33d6d5aa6': 'GOOGL'
};

app.use(express.static('public'));
app.use(express.json());

// API endpoint to get MAANG oracle status
app.get('/api/status', async (req, res) => {
    try {
        // Try to use aggregator first, fallback to direct oracle
        let price, timestamp, isStale, assetName, feedStatus;
        
        try {
            // Use OracleAggregator if available
            if (aggregatorAddress !== "0x0000000000000000000000000000000000000000") {
                const [aggPrice, aggTimestamp] = await aggregator.getAggregatedPrice();
                const [canUpdate, reasonCode] = await aggregator.canUpdate();
                const activeCount = await aggregator.getActiveOracleCount();
                
                price = aggPrice;
                timestamp = aggTimestamp;
                isStale = !canUpdate;
                assetName = "MAANG/USD (Aggregated)";
                
                // Get feed breakdown from MAANG oracle
                const breakdown = await maangOracle.getMAANGBreakdown();
                feedStatus = [];
                
                for (let i = 0; i < breakdown.feedIds.length; i++) {
                    const feedId = breakdown.feedIds[i];
                    const symbol = maangFeeds[feedId] || 'UNKNOWN';
                    feedStatus.push({
                        symbol,
                        price: Number(breakdown.prices[i]) / 1e13, // Convert from 18 decimals
                        timestamp: Number(breakdown.timestamps[i]),
                        isValid: breakdown.isValid[i]
                    });
                }
            } else {
                throw new Error("Aggregator not deployed yet");
            }
        } catch (aggError) {
            // Fallback to direct MAANG oracle
            console.log("Using MAANG oracle directly:", aggError.message);
            
            const [directPrice, directTimestamp] = await maangOracle.viewPrice();
            const directIsStale = await maangOracle.isStale();
            const directAssetName = await maangOracle.getAssetName();
            
            price = directPrice;
            timestamp = directTimestamp;
            isStale = directIsStale;
            assetName = directAssetName;
            
            const breakdown = await maangOracle.getMAANGBreakdown();
            feedStatus = [];
            
            for (let i = 0; i < breakdown.feedIds.length; i++) {
                const feedId = breakdown.feedIds[i];
                const symbol = maangFeeds[feedId] || 'UNKNOWN';
                feedStatus.push({
                    symbol,
                    price: Number(breakdown.prices[i]) / 1e13, // Convert from 18 decimals
                    timestamp: Number(breakdown.timestamps[i]),
                    isValid: breakdown.isValid[i]
                });
            }
        }

        res.json({
            success: true,
            data: {
                assetName,
                price: Number(price) / 1e13, // Convert from 18 decimals
                timestamp: Number(timestamp),
                isStale,
                feeds: feedStatus,
                lastUpdate: new Date(Number(timestamp) * 1000).toISOString()
            }
        });
    } catch (error) {
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

// Health check endpoint
app.get('/health', (req, res) => {
    res.json({ status: 'healthy', timestamp: new Date().toISOString() });
});

app.listen(PORT, () => {
    console.log(`🚀 MAANG Oracle Dashboard running on port ${PORT}`);
    console.log(`📊 Dashboard: http://localhost:${PORT}`);
    console.log(`🔍 API: http://localhost:${PORT}/api/status`);
});
