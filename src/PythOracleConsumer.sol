// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "./interfaces/IOracle.sol";

/**
 * @title PythOracleConsumer
 * @author DRI Protocol Team
 * @notice A unified Pyth oracle consumer that implements the IOracle interface
 * @dev This contract merges the functionality of WorkingPyth and WorkingPriceConsumer
 *      to provide a single, clean interface for consuming Pyth price feeds.
 * 
 * Key Features:
 * - Implements IOracle interface for DRI Protocol compatibility
 * - Stores and manages multiple price feeds
 * - Provides both individual and aggregated price access
 * - Includes staleness detection and validation
 * - Emits events for price updates and system status
 */
contract PythOracleConsumer is IOracle {
    // ==================== STATE VARIABLES ====================
    
    /// @notice Price feed data structure
    struct PriceFeed {
        int64 price;        // Current price (8 decimals from Pyth)
        uint256 timestamp;  // Last update timestamp
        bool isValid;       // Whether this feed has valid data
    }
    
    /// @notice Maximum age for price data to be considered fresh (30 seconds)
    uint256 public constant MAX_AGE = 30;
    
    /// @notice Number of decimal places in the original Pyth price feeds (8 decimals)
    uint8 public constant SOURCE_DECIMALS = 8;
    
    /// @notice Number of decimal places for normalized prices (18 decimals)
    uint8 public constant NORMALIZED_DECIMALS = 18;
    
    /// @notice Scaling factor to convert from 8 decimals to 18 decimals
    uint256 public constant SCALE_FACTOR = 1e10;
    
    /// @notice Owner of the contract (can update prices)
    address public owner;
    
    /// @notice Mapping from feed ID to price data
    mapping(bytes32 => PriceFeed) public priceFeeds;
    
    /// @notice Array of all registered feed IDs
    bytes32[] public feedIds;
    
    /// @notice Mapping to check if a feed ID is registered
    mapping(bytes32 => bool) public isFeedRegistered;
    
    /// @notice Minimum number of valid feeds required for aggregated price
    uint256 public minValidFeeds = 3;
    
    // ==================== EVENTS ====================
    
    /// @notice Emitted when a price feed is updated
    event PriceFeedUpdated(bytes32 indexed feedId, int64 price, uint256 timestamp);
    
    /// @notice Emitted when a new feed is registered
    event FeedRegistered(bytes32 indexed feedId);
    
    /// @notice Emitted when the minimum valid feeds requirement is updated
    event MinValidFeedsUpdated(uint256 oldMin, uint256 newMin);
    
    /// @notice Emitted when the owner is changed
    event OwnershipTransferred(address indexed previousOwner, address indexed newOwner);
    
    // ==================== ERRORS ====================
    
    error Unauthorized();
    error InvalidPrice(int64 price);
    error InvalidTimestamp(uint256 timestamp);
    error FeedNotRegistered(bytes32 feedId);
    error InsufficientValidFeeds(uint256 validFeeds, uint256 minRequired);
    error PriceStale(uint256 age, uint256 maxAge);
    
    // ==================== MODIFIERS ====================
    
    modifier onlyOwner() {
        if (msg.sender != owner) revert Unauthorized();
        _;
    }
    
    // ==================== CONSTRUCTOR ====================
    
    constructor() {
        owner = msg.sender;
        emit OwnershipTransferred(address(0), msg.sender);
    }
    
    // ==================== ERC165 SUPPORT ====================
    
    /**
     * @notice Supports interface for ERC165
     * @dev Returns true if the contract implements the interface
     * @param interfaceId The interface ID to check
     * @return True if the interface is supported
     */
    function supportsInterface(bytes4 interfaceId) external pure returns (bool) {
        return interfaceId == type(IOracle).interfaceId;
    }
    
    // ==================== CORE FUNCTIONS ====================
    
    /**
     * @notice Updates multiple price feeds with new data
     * @dev This function is called by the keeper to update prices
     * @param feedIds_ Array of feed IDs to update
     * @param prices Array of new prices (8 decimals)
     * @param timestamps Array of timestamps for each price update
     */
    function updatePriceFeeds(
        bytes32[] calldata feedIds_,
        int64[] calldata prices,
        uint256[] calldata timestamps
    ) external onlyOwner {
        require(
            feedIds_.length == prices.length && prices.length == timestamps.length,
            "Arrays length mismatch"
        );
        
        for (uint256 i = 0; i < feedIds_.length; i++) {
            _updateSingleFeed(feedIds_[i], prices[i], timestamps[i]);
        }
    }
    
    /**
     * @notice Updates a single price feed
     * @dev Internal function to update individual feed data
     * @param feedId The feed ID to update
     * @param price New price (8 decimals)
     * @param timestamp New timestamp
     */
    function _updateSingleFeed(
        bytes32 feedId,
        int64 price,
        uint256 timestamp
    ) internal {
        if (price <= 0) revert InvalidPrice(price);
        if (timestamp == 0) revert InvalidTimestamp(timestamp);
        
        priceFeeds[feedId] = PriceFeed({
            price: price,
            timestamp: timestamp,
            isValid: true
        });
        
        emit PriceFeedUpdated(feedId, price, timestamp);
    }
    
    /**
     * @notice Registers a new price feed
     * @dev Only owner can register new feeds
     * @param feedId The feed ID to register
     */
    function registerFeed(bytes32 feedId) external onlyOwner {
        if (isFeedRegistered[feedId]) {
            revert("Feed already registered");
        }
        
        feedIds.push(feedId);
        isFeedRegistered[feedId] = true;
        
        emit FeedRegistered(feedId);
    }
    
    /**
     * @notice Updates the minimum valid feeds requirement
     * @dev Only owner can update this value
     * @param newMinValidFeeds New minimum number of valid feeds required
     */
    function setMinValidFeeds(uint256 newMinValidFeeds) external onlyOwner {
        uint256 oldMin = minValidFeeds;
        minValidFeeds = newMinValidFeeds;
        emit MinValidFeedsUpdated(oldMin, newMinValidFeeds);
    }
    
    /**
     * @notice Transfers ownership of the contract
     * @dev Only current owner can transfer ownership
     * @param newOwner Address of the new owner
     */
    function transferOwnership(address newOwner) external onlyOwner {
        require(newOwner != address(0), "New owner cannot be zero address");
        address oldOwner = owner;
        owner = newOwner;
        emit OwnershipTransferred(oldOwner, newOwner);
    }
    
    // ==================== IOracle INTERFACE IMPLEMENTATION ====================
    
    /**
     * @notice Retrieves the latest aggregated price and timestamp
     * @dev Implements IOracle interface - returns weighted average of all valid feeds
     * @return price The aggregated price scaled to 18 decimals
     * @return timestamp The timestamp of the most recent update
     */
    function getPrice() external returns (uint256 price, uint256 timestamp) {
        (price, timestamp) = _calculateAggregatedPrice();
        return (price, timestamp);
    }
    
    /**
     * @notice Get price data without emitting events (for off-chain reads)
     * @dev Implements IOracle interface - view-only function
     * @return price The current aggregated price in 18 decimals
     * @return timestamp The timestamp of the most recent update
     */
    function viewPrice() external view returns (uint256 price, uint256 timestamp) {
        (price, timestamp) = _calculateAggregatedPriceView();
        return (price, timestamp);
    }
    
    /**
     * @notice Checks if the oracle's price data is considered stale
     * @dev Implements IOracle interface - checks if any valid feeds are stale
     * @return stale True if the price data is too old to be reliable
     */
    function isStale() external view returns (bool stale) {
        uint256 validFeeds = _getValidFeedCount();
        if (validFeeds < minValidFeeds) return true;
        
        // Check if any valid feed is stale
        for (uint256 i = 0; i < feedIds.length; i++) {
            bytes32 feedId = feedIds[i];
            if (isFeedRegistered[feedId] && priceFeeds[feedId].isValid) {
                if (block.timestamp - priceFeeds[feedId].timestamp > MAX_AGE) {
                    return true;
                }
            }
        }
        
        return false;
    }
    
    /**
     * @notice Returns the decimal precision of the normalized price data
     * @dev Implements IOracle interface - always returns 18 for normalized prices
     * @return decimals The number of decimal places (18)
     */
    function getDecimals() external pure returns (uint8 decimals) {
        return NORMALIZED_DECIMALS;
    }
    
    // ==================== UTILITY FUNCTIONS ====================
    
    /**
     * @notice Gets the latest price for a specific feed
     * @dev Returns the raw price data for a specific feed ID
     * @param feedId The feed ID to query
     * @return price The current price (8 decimals)
     * @return timestamp The timestamp of the last update
     * @return isValid Whether the feed has valid data
     */
    function getLatestPrice(bytes32 feedId) external view returns (int64 price, uint256 timestamp, bool isValid) {
        if (!isFeedRegistered[feedId]) revert FeedNotRegistered(feedId);
        
        PriceFeed memory feed = priceFeeds[feedId];
        return (feed.price, feed.timestamp, feed.isValid);
    }
    
    /**
     * @notice Gets the latest price for a specific feed (legacy compatibility)
     * @dev Returns the raw price data for a specific feed ID (matches WorkingPyth interface)
     * @param feedId The feed ID to query
     * @return price The current price (8 decimals)
     * @return timestamp The timestamp of the last update
     */
    function getLatestPriceLegacy(bytes32 feedId) external view returns (int64 price, uint256 timestamp) {
        if (!isFeedRegistered[feedId]) revert FeedNotRegistered(feedId);
        
        PriceFeed memory feed = priceFeeds[feedId];
        return (feed.price, feed.timestamp);
    }
    
    /**
     * @notice Gets all registered feed IDs
     * @dev Returns the array of all registered feed IDs
     * @return Array of feed IDs
     */
    function getAllFeedIds() external view returns (bytes32[] memory) {
        return feedIds;
    }
    
    /**
     * @notice Gets the count of valid feeds
     * @dev Returns the number of feeds with valid, non-stale data
     * @return count The number of valid feeds
     */
    function getValidFeedCount() external view returns (uint256 count) {
        return _getValidFeedCount();
    }
    
    /**
     * @notice Gets the count of valid feeds (internal)
     * @dev Internal function to count valid feeds
     * @return count The number of valid feeds
     */
    function _getValidFeedCount() internal view returns (uint256 count) {
        for (uint256 i = 0; i < feedIds.length; i++) {
            bytes32 feedId = feedIds[i];
            if (isFeedRegistered[feedId] && priceFeeds[feedId].isValid) {
                if (block.timestamp - priceFeeds[feedId].timestamp <= MAX_AGE) {
                    count++;
                }
            }
        }
        return count;
    }
    
    /**
     * @notice Calculates the aggregated price (mutative version)
     * @dev Calculates weighted average of all valid feeds
     * @return price The aggregated price scaled to 18 decimals
     * @return timestamp The timestamp of the most recent update
     */
    function _calculateAggregatedPrice() internal returns (uint256 price, uint256 timestamp) {
        uint256 validFeeds = _getValidFeedCount();
        if (validFeeds < minValidFeeds) {
            revert InsufficientValidFeeds(validFeeds, minValidFeeds);
        }
        
        uint256 totalPrice = 0;
        uint256 latestTimestamp = 0;
        uint256 validCount = 0;
        
        for (uint256 i = 0; i < feedIds.length; i++) {
            bytes32 feedId = feedIds[i];
            if (isFeedRegistered[feedId] && priceFeeds[feedId].isValid) {
                PriceFeed memory feed = priceFeeds[feedId];
                if (block.timestamp - feed.timestamp <= MAX_AGE) {
                    totalPrice += uint256(int256(feed.price));
                    if (feed.timestamp > latestTimestamp) {
                        latestTimestamp = feed.timestamp;
                    }
                    validCount++;
                }
            }
        }
        
        if (validCount == 0) {
            revert InsufficientValidFeeds(0, minValidFeeds);
        }
        
        price = (totalPrice * SCALE_FACTOR) / validCount;
        timestamp = latestTimestamp;
    }
    
    /**
     * @notice Calculates the aggregated price (view version)
     * @dev Calculates weighted average of all valid feeds (view-only)
     * @return price The aggregated price scaled to 18 decimals
     * @return timestamp The timestamp of the most recent update
     */
    function _calculateAggregatedPriceView() internal view returns (uint256 price, uint256 timestamp) {
        uint256 validFeeds = _getValidFeedCount();
        if (validFeeds < minValidFeeds) {
            revert InsufficientValidFeeds(validFeeds, minValidFeeds);
        }
        
        uint256 totalPrice = 0;
        uint256 latestTimestamp = 0;
        uint256 validCount = 0;
        
        for (uint256 i = 0; i < feedIds.length; i++) {
            bytes32 feedId = feedIds[i];
            if (isFeedRegistered[feedId] && priceFeeds[feedId].isValid) {
                PriceFeed memory feed = priceFeeds[feedId];
                if (block.timestamp - feed.timestamp <= MAX_AGE) {
                    totalPrice += uint256(int256(feed.price));
                    if (feed.timestamp > latestTimestamp) {
                        latestTimestamp = feed.timestamp;
                    }
                    validCount++;
                }
            }
        }
        
        if (validCount == 0) {
            revert InsufficientValidFeeds(0, minValidFeeds);
        }
        
        price = (totalPrice * SCALE_FACTOR) / validCount;
        timestamp = latestTimestamp;
    }
}
