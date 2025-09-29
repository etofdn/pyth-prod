// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title IOracle
 * @notice Standard oracle interface for price feeds
 */
interface IOracle {
    /**
     * @notice Get the latest price and timestamp
     * @return price The latest price (18 decimals)
     * @return timestamp The timestamp of the price
     */
    function getPrice() external returns (uint256 price, uint256 timestamp);
    
    /**
     * @notice Get the latest price and timestamp (view function)
     * @return price The latest price (18 decimals)
     * @return timestamp The timestamp of the price
     */
    function viewPrice() external view returns (uint256 price, uint256 timestamp);
    
    /**
     * @notice Check if the oracle is stale
     * @return True if the oracle is stale
     */
    function isStale() external view returns (bool);
    
    /**
     * @notice Get the number of decimals for the price
     * @return The number of decimals
     */
    function getDecimals() external pure returns (uint8);
}