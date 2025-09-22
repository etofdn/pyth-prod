// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Script.sol";
import "../src/OracleAggregator.sol";
import "../src/oracles/MAANGPythOracle.sol";

contract DeployOracleAggregator is Script {
    function run() external {
        uint256 deployerPrivateKey = vm.envUint("PRIVATE_KEY");
        vm.startBroadcast(deployerPrivateKey);

        console.log("=== DEPLOYING ORACLE AGGREGATOR SYSTEM ===");
        console.log("Deployer address:", vm.addr(deployerPrivateKey));

        // Existing contract addresses
        address workingPythAddress = 0x431904FE789A377d166eEFbaE1681239C17B134b;
        address maangOracleAddress = 0x7b0c3c7557897dd2bc9c9435100467942905411c;
        
        console.log("WorkingPyth address:", workingPythAddress);
        console.log("MAANG Oracle address:", maangOracleAddress);

        // Deploy OracleAggregator
        address governance = vm.addr(deployerPrivateKey);
        OracleAggregator aggregator = new OracleAggregator(
            governance,
            maangOracleAddress
        );

        console.log("OracleAggregator deployed at:", address(aggregator));

        // Grant governance role to deployer
        aggregator.grantRole(aggregator.GOV_ROLE(), governance);
        console.log("Granted GOV_ROLE to:", governance);

        // Add MAANG oracle to aggregator with 100% weight (since it's the only oracle)
        aggregator.addOracleAdvanced(
            maangOracleAddress,
            10000, // 100% weight
            14400, // 4 hours max age for stocks
            1500   // 15% max deviation
        );
        console.log("Added MAANG Oracle to aggregator with 100% weight");

        // Test the aggregator
        console.log("\n=== TESTING ORACLE AGGREGATOR ===");
        
        try aggregator.getAggregatedPrice() returns (uint256 price, uint256 timestamp) {
            console.log("Aggregated Price:", price);
            console.log("Timestamp:", timestamp);
            console.log("Price in USD:", price / 1e13); // Convert from 18 decimals
        } catch Error(string memory reason) {
            console.log("Error getting aggregated price:", reason);
        }

        try aggregator.getActiveOracleCount() returns (uint256 count) {
            console.log("Active Oracle Count:", count);
        } catch {
            console.log("Error getting active oracle count");
        }

        try aggregator.canUpdate() returns (bool canUpdate, uint8 reasonCode) {
            console.log("Can Update:", canUpdate);
            console.log("Reason Code:", reasonCode);
        } catch {
            console.log("Error checking if can update");
        }

        vm.stopBroadcast();

        console.log("\n=== ORACLE AGGREGATOR DEPLOYMENT COMPLETE ===");
        console.log("OracleAggregator:", address(aggregator));
        console.log("Governance:", governance);
        console.log("MAANG Oracle:", maangOracleAddress);
        console.log("WorkingPyth:", workingPythAddress);
        
        console.log("\n=== NEXT STEPS ===");
        console.log("1. Update keeper to call aggregator.updatePrice()");
        console.log("2. External contracts should use aggregator.getAggregatedPrice()");
        console.log("3. Dashboard should query aggregator for price data");
    }
}
