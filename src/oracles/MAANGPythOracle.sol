// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "../interfaces/IOracle.sol";
import "../WorkingPyth.sol";

/**
 * @title MAANGPythOracle  
 * @notice Single oracle that aggregates META, AAPL, AMZN, NVDA, GOOGL into one index
 * @dev Implements IOracle interface for integration with OracleAggregator
 * @dev Uses direct Pyth contract integration with verified Hermes API feed IDs
 */
contract MAANGPythOracle is IOracle {
    
    // ===== PYTH INTEGRATION =====
    WorkingPyth public immutable pythContract;
    
    // ===== MAANG FEED IDS =====
    bytes32 public constant META_FEED_ID = 0x78a3e3b8e676a8f73c439f5d749737034b139bbbe899ba5775216fba596607fe;
    bytes32 public constant AAPL_FEED_ID = 0x49f6b65cb1de6b10eaf75e7c03ca029c306d0357e91b5311b175084a5ad55688;
    bytes32 public constant AMZN_FEED_ID = 0xb5d0e0fa58a1f8b81498ae670ce93c872d14434b72c364885d4fa1b257cbb07a;
    bytes32 public constant NVDA_FEED_ID = 0xb1073854ed24cbc755dc527418f52b7d271f6cc967bbf8d8129112b18860a593;
    bytes32 public constant GOOGL_FEED_ID = 0x5a48c03e9b9cb337801073ed9d166817473697efff0d138874e0f6a33d6d5aa6;
    
    // ===== CONFIGURATION =====
    uint256 public immutable maxAge;           // Max staleness (e.g., 4 hours for stocks)
    uint256 public immutable minValidFeeds;    // Minimum feeds needed (e.g., 3 out of 5)
    uint8 public constant SOURCE_DECIMALS = 5;  // Pyth stock feeds use 5 decimals
    
    // ===== WEIGHTS FOR MAANG INDEX =====
    // Equal weight approach (20% each)
    uint256 public constant META_WEIGHT = 2000;   // 20%
    uint256 public constant AAPL_WEIGHT = 2000;   // 20%
    uint256 public constant AMZN_WEIGHT = 2000;   // 20%
    uint256 public constant NVDA_WEIGHT = 2000;   // 20%
    uint256 public constant GOOGL_WEIGHT = 2000;  // 20%
    uint256 public constant TOTAL_WEIGHT = 10000; // 100%
    
    // ===== EVENTS =====
    event MAANGIndexUpdated(uint256 indexPrice, uint256 timestamp, uint256 validFeeds);
    event FeedFiltered(bytes32 indexed feedId, uint256 price, uint256 timestamp, string reason);
    
    // ===== ERRORS =====
    error InsufficientValidFeeds(uint256 valid, uint256 required);
    error AllFeedsStale();
    error InvalidPrice();
    error SourceUnavailable();
    
    constructor(
        address _pythContract,
        uint256 _maxAge,           // e.g., 14400 (4 hours)
        uint256 _minValidFeeds     // e.g., 3 (need 3 out of 5 stocks)
    ) {
        pythContract = WorkingPyth(_pythContract);
        maxAge = _maxAge;
        minValidFeeds = _minValidFeeds;
    }
    
    // ===== IORACLE IMPLEMENTATION =====
    
    function getPrice() external returns (uint256 price, uint256 timestamp) {
        (price, timestamp) = _calculateMAANGIndex();
        emit MAANGIndexUpdated(price, timestamp, _getValidFeedCount());
    }
    
    function viewPrice() external view returns (uint256 price, uint256 timestamp) {
        return _calculateMAANGIndexView();
    }
    
    function isStale() external view returns (bool) {
        uint256 validFeeds = _getValidFeedCount();
        if (validFeeds < minValidFeeds) {
            return true; // Consider stale if insufficient valid feeds
        }
        (, uint256 timestamp) = _calculateMAANGIndexView();
        return timestamp == 0 || block.timestamp - timestamp > maxAge;
    }
    
    function getDecimals() external pure returns (uint8) {
        return SOURCE_DECIMALS; // Return source decimals (5) for consistency
    }
    
    // ===== MAANG INDEX CALCULATION =====
    
    function _calculateMAANGIndex() internal returns (uint256 indexPrice, uint256 latestTimestamp) {
        bytes32[5] memory feedIds = [META_FEED_ID, AAPL_FEED_ID, AMZN_FEED_ID, NVDA_FEED_ID, GOOGL_FEED_ID];
        uint256[5] memory weights = [META_WEIGHT, AAPL_WEIGHT, AMZN_WEIGHT, NVDA_WEIGHT, GOOGL_WEIGHT];
        
        uint256 weightedSum = 0;
        uint256 validWeight = 0;
        uint256 validCount = 0;
        latestTimestamp = 0;
        
        for (uint256 i = 0; i < 5; i++) {
            bytes32 feedId = feedIds[i];
            
            try pythContract.getLatestPrice(feedId) returns (int64 price, uint256 timestamp) {
                // Validation checks
                if (price <= 0) {
                    emit FeedFiltered(feedId, 0, timestamp, "Invalid price");
                    continue;
                }
                
                if (timestamp == 0 || block.timestamp - timestamp > maxAge) {
                    emit FeedFiltered(feedId, uint256(int256(price)), timestamp, "Stale data");
                    continue;
                }
                
                // Valid feed - add to weighted sum
                uint256 scaledPrice = _scalePrice(uint256(int256(price)));
                uint256 weight = weights[i];
                
                weightedSum += scaledPrice * weight;
                validWeight += weight;
                validCount++;
                
                // Track latest timestamp
                if (timestamp > latestTimestamp) {
                    latestTimestamp = timestamp;
                }
                
            } catch {
                emit FeedFiltered(feedId, 0, 0, "Feed unavailable");
                continue;
            }
        }
        
        // Require minimum valid feeds
        if (validCount < minValidFeeds) {
            revert InsufficientValidFeeds(validCount, minValidFeeds);
        }
        
        // Calculate weighted average
        indexPrice = weightedSum / validWeight;
        
        // Use current timestamp if no valid timestamps found
        if (latestTimestamp == 0) {
            latestTimestamp = block.timestamp;
        }
    }
    
    function _calculateMAANGIndexView() internal view returns (uint256 indexPrice, uint256 latestTimestamp) {
        bytes32[5] memory feedIds = [META_FEED_ID, AAPL_FEED_ID, AMZN_FEED_ID, NVDA_FEED_ID, GOOGL_FEED_ID];
        uint256[5] memory weights = [META_WEIGHT, AAPL_WEIGHT, AMZN_WEIGHT, NVDA_WEIGHT, GOOGL_WEIGHT];
        
        uint256 weightedSum = 0;
        uint256 validWeight = 0;
        uint256 validCount = 0;
        latestTimestamp = 0;
        
        for (uint256 i = 0; i < 5; i++) {
            bytes32 feedId = feedIds[i];
            
            try pythContract.getLatestPrice(feedId) returns (int64 price, uint256 timestamp) {
                // Validation checks
                if (price <= 0) {
                    continue;
                }
                
                if (timestamp == 0 || block.timestamp - timestamp > maxAge) {
                    continue;
                }
                
                // Valid feed - add to weighted sum
                uint256 scaledPrice = _scalePrice(uint256(int256(price)));
                uint256 weight = weights[i];
                
                weightedSum += scaledPrice * weight;
                validWeight += weight;
                validCount++;
                
                // Track latest timestamp
                if (timestamp > latestTimestamp) {
                    latestTimestamp = timestamp;
                }
                
            } catch {
                continue;
            }
        }
        
        // Require minimum valid feeds
        if (validCount < minValidFeeds) {
            revert InsufficientValidFeeds(validCount, minValidFeeds);
        }
        
        // Calculate weighted average
        indexPrice = weightedSum / validWeight;
        
        // Use current timestamp if no valid timestamps found
        if (latestTimestamp == 0) {
            latestTimestamp = block.timestamp;
        }
    }
    
    function _getFeedPrice(bytes32 feedId) internal view returns (int64 price, uint256 timestamp) {
        // Direct call - let errors bubble up
        return pythContract.getLatestPrice(feedId);
    }
    
    function _scalePrice(uint256 rawPrice) internal pure returns (uint256) {
        // Convert from 5 decimals to 18 decimals
        // rawPrice is in 5 decimals, we need 18 decimals
        return rawPrice * (10 ** (18 - SOURCE_DECIMALS)); // * 1e13
    }
    
    function _getValidFeedCount() internal view returns (uint256) {
        bytes32[5] memory feedIds = [META_FEED_ID, AAPL_FEED_ID, AMZN_FEED_ID, NVDA_FEED_ID, GOOGL_FEED_ID];
        uint256 validCount = 0;
        
        for (uint256 i = 0; i < 5; i++) {
            try pythContract.getLatestPrice(feedIds[i]) returns (int64 price, uint256 timestamp) {
                if (price > 0 && timestamp > 0 && block.timestamp - timestamp <= maxAge) {
                    validCount++;
                }
            } catch {
                continue;
            }
        }
        
        return validCount;
    }
    
    // ===== UTILITY FUNCTIONS =====
    
    // ===== ORACLE AGGREGATOR COMPATIBILITY =====
    
    function getMAAGIndex() external view returns (uint256 averagePrice, uint256 timestamp, uint256 activeFeeds, uint256 totalValue) {
        (averagePrice, timestamp) = _calculateMAANGIndexView();
        activeFeeds = _getValidFeedCount();
        totalValue = averagePrice * activeFeeds; // Total value of all active feeds
    }
    
    function getAllPrices() external view returns (
        bytes32[] memory feedIds,
        uint256[] memory prices,
        uint256[] memory timestamps,
        bool[] memory isActive
    ) {
        feedIds = new bytes32[](5);
        prices = new uint256[](5);
        timestamps = new uint256[](5);
        isActive = new bool[](5);
        
        bytes32[5] memory feeds = [META_FEED_ID, AAPL_FEED_ID, AMZN_FEED_ID, NVDA_FEED_ID, GOOGL_FEED_ID];
        
        for (uint256 i = 0; i < 5; i++) {
            feedIds[i] = feeds[i];
            
            try pythContract.getLatestPrice(feeds[i]) returns (int64 price, uint256 timestamp) {
                prices[i] = _scalePrice(uint256(int256(price)));
                timestamps[i] = timestamp;
                isActive[i] = price > 0 && timestamp > 0 && block.timestamp - timestamp <= maxAge;
            } catch {
                prices[i] = 0;
                timestamps[i] = 0;
                isActive[i] = false;
            }
        }
    }
    
    // Keep the old function for backward compatibility
    function getMAANGBreakdown() external view returns (
        bytes32[] memory feedIds,
        uint256[] memory prices,
        uint256[] memory timestamps,
        bool[] memory isValid
    ) {
        feedIds = new bytes32[](5);
        prices = new uint256[](5);
        timestamps = new uint256[](5);
        isValid = new bool[](5);
        
        bytes32[5] memory feeds = [META_FEED_ID, AAPL_FEED_ID, AMZN_FEED_ID, NVDA_FEED_ID, GOOGL_FEED_ID];
        
        for (uint256 i = 0; i < 5; i++) {
            feedIds[i] = feeds[i];
            
            try pythContract.getLatestPrice(feeds[i]) returns (int64 price, uint256 timestamp) {
                prices[i] = _scalePrice(uint256(int256(price)));
                timestamps[i] = timestamp;
                isValid[i] = price > 0 && timestamp > 0 && block.timestamp - timestamp <= maxAge;
            } catch {
                prices[i] = 0;
                timestamps[i] = 0;
                isValid[i] = false;
            }
        }
    }
    
    function getMAANGIndex() external view returns (uint256 indexPrice, uint256 timestamp, uint256 validFeeds) {
        (indexPrice, timestamp) = _calculateMAANGIndexView();
        validFeeds = _getValidFeedCount();
    }
    
    function getAssetName() external pure returns (string memory) {
        return "MAANG/USD";
    }
    
    function getMaxAge() external view returns (uint256) {
        return maxAge;
    }
    
    function getMinValidFeeds() external view returns (uint256) {
        return minValidFeeds;
    }
    
    function getTotalWeight() external pure returns (uint256) {
        return TOTAL_WEIGHT;
    }
}
