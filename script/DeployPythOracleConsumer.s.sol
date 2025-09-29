// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Script.sol";
import "../src/PythOracleConsumer.sol";

/**
 * @title DeployPythOracleConsumer
 * @notice Deployment script for the unified PythOracleConsumer contract
 * @dev This script deploys the merged contract and registers all MAANG feeds
 */
contract DeployPythOracleConsumer is Script {
    // MAANG stock feed IDs
    bytes32 constant META_FEED_ID = 0x78a3e3b8e676a8f73c439f5d749737034b139bbbe899ba5775216fba596607fe;
    bytes32 constant AAPL_FEED_ID = 0x49f6b65cb1de6b10eaf75e7c03ca029c306d0357e91b5311b175084a5ad55688;
    bytes32 constant AMZN_FEED_ID = 0xb5d0e0fa58a1f8b81498ae670ce93c872d14434b72c364885d4fa1b257cbb07a;
    bytes32 constant NVDA_FEED_ID = 0xb1073854ed24cbc755dc527418f52b7d271f6cc967bbf8d8129112b18860a593;
    bytes32 constant GOOGL_FEED_ID = 0x5a48c03e9b9cb337801073ed9d166817473697efff0d138874e0f6a33d6d5aa6;
    
    function run() external {
        uint256 deployerPrivateKey = vm.envUint("PRIVATE_KEY");
        address deployer = vm.addr(deployerPrivateKey);
        
        console.log("Deploying PythOracleConsumer...");
        console.log("Deployer:", deployer);
        
        vm.startBroadcast(deployerPrivateKey);
        
        // Deploy the contract
        PythOracleConsumer consumer = new PythOracleConsumer();
        
        console.log("PythOracleConsumer deployed at:", address(consumer));
        
        // Register all MAANG feeds
        console.log("Registering MAANG feeds...");
        
        consumer.registerFeed(META_FEED_ID);
        console.log("Registered META feed");
        
        consumer.registerFeed(AAPL_FEED_ID);
        console.log("Registered AAPL feed");
        
        consumer.registerFeed(AMZN_FEED_ID);
        console.log("Registered AMZN feed");
        
        consumer.registerFeed(NVDA_FEED_ID);
        console.log("Registered NVDA feed");
        
        consumer.registerFeed(GOOGL_FEED_ID);
        console.log("Registered GOOGL feed");
        
        // Set minimum valid feeds to 3
        consumer.setMinValidFeeds(3);
        console.log("Set minimum valid feeds to 3");
        
        vm.stopBroadcast();
        
        console.log("=== DEPLOYMENT COMPLETE ===");
        console.log("Contract Address:", address(consumer));
        console.log("Owner:", consumer.owner());
        console.log("Min Valid Feeds:", consumer.minValidFeeds());
        console.log("Source Decimals:", consumer.SOURCE_DECIMALS());
        console.log("Normalized Decimals:", consumer.NORMALIZED_DECIMALS());
        console.log("Max Age:", consumer.MAX_AGE());
        
        // Test the contract
        console.log("\n=== TESTING CONTRACT ===");
        
        // Check if feeds are registered
        bytes32[] memory feedIds = consumer.getAllFeedIds();
        console.log("Registered feeds count:", feedIds.length);
        
        for (uint256 i = 0; i < feedIds.length; i++) {
            console.log("Feed", i, ":", vm.toString(feedIds[i]));
        }
        
        console.log("\n=== INTEGRATION INSTRUCTIONS ===");
        console.log("1. Update your keeper to use this contract address");
        console.log("2. Your dev can now use IOracle interface directly");
        console.log("3. Contract implements both individual and aggregated price access");
        console.log("4. All prices are normalized to 18 decimals");
    }
}
