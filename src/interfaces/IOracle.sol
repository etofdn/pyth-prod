// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title IOracle
 * @notice Standard interface for oracle integration with DRI Protocol
 * @dev All oracles must implement this interface for OracleAggregator compatibility
 */
interface IOracle {
    /**
     * @notice Get price with state changes (can emit events)
     * @return price Price in 18 decimals (wei scale)
     * @return timestamp Unix timestamp of price update
     */
    function getPrice() external returns (uint256 price, uint256 timestamp);
    
    /**
     * @notice Get price without state changes (view only)
     * @return price Price in 18 decimals (wei scale) 
     * @return timestamp Unix timestamp of price update
     */
    function viewPrice() external view returns (uint256 price, uint256 timestamp);
    
    /**
     * @notice Check if price data is stale
     * @return isStale True if data is too old to use
     */
    function isStale() external view returns (bool isStale);
    
    /**
     * @notice Get source decimal precision
     * @return decimals Number of decimals in source data
     */
    function getDecimals() external view returns (uint8 decimals);
}
