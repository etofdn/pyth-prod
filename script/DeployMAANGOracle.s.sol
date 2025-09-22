// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Script.sol";
import "../src/oracles/MAANGPythOracle.sol";

contract DeployMAANGOracle is Script {
    function run() external {
        uint256 deployerPrivateKey = vm.envUint("PRIVATE_KEY");
        vm.startBroadcast(deployerPrivateKey);

        console.log("=== DEPLOYING MAANG CUMULATIVE ORACLE ===");
        console.log("Deployer address:", vm.addr(deployerPrivateKey));

        // Use existing WorkingPyth contract address
        address pythContractAddress = 0x431904FE789A377d166eEFbaE1681239C17B134b;
        
        // Configuration for MAANG oracle
        uint256 maxAge = 14400;        // 4 hours max age for stocks
        uint256 minValidFeeds = 3;     // Need at least 3 out of 5 stocks
        
        console.log("WorkingPyth Contract:", pythContractAddress);
        console.log("Max Age:", maxAge, "seconds (4 hours)");
        console.log("Min Valid Feeds:", minValidFeeds, "out of 5");

        // Deploy MAANG oracle
        MAANGPythOracle maangOracle = new MAANGPythOracle(
            pythContractAddress,
            maxAge,
            minValidFeeds
        );

        console.log("MAANG Oracle deployed at:", address(maangOracle));

        // Test the oracle
        console.log("\n=== TESTING MAANG ORACLE ===");
        
        try maangOracle.getAssetName() returns (string memory assetName) {
            console.log("Asset Name:", assetName);
        } catch {
            console.log("Failed to get asset name");
        }

        try maangOracle.getTotalWeight() returns (uint256 totalWeight) {
            console.log("Total Weight:", totalWeight);
        } catch {
            console.log("Failed to get total weight");
        }

        try maangOracle.viewPrice() returns (uint256 price, uint256 timestamp) {
            console.log("MAANG Index Price:", price);
            console.log("Price Timestamp:", timestamp);
            console.log("Human readable price: $%s", price / 1e13); // Convert from 18 decimals
        } catch {
            console.log("Failed to get price");
        }

        try maangOracle.isStale() returns (bool stale) {
            console.log("Is Stale:", stale);
        } catch {
            console.log("Failed to check staleness");
        }

        try maangOracle.getMAANGBreakdown() returns (
            bytes32[] memory feedIds,
            uint256[] memory prices,
            uint256[] memory timestamps,
            bool[] memory isValid,
            string[] memory symbols
        ) {
            console.log("\n=== MAANG BREAKDOWN ===");
            for (uint256 i = 0; i < symbols.length; i++) {
                console.log("%s: $%s (Valid: %s)", 
                    symbols[i], 
                    prices[i] / 1e13, 
                    isValid[i] ? "YES" : "NO"
                );
            }
        } catch {
            console.log("Failed to get breakdown");
        }

        vm.stopBroadcast();

        console.log("\n=== MAANG ORACLE DEPLOYMENT COMPLETE ===");
        console.log("MAANG Oracle Address:", address(maangOracle));
        console.log("Integration with OracleAggregator:");
        console.log("  aggregator.addOracleAdvanced(");
        console.log("    address(maangOracle),");
        console.log("    10000,  // 100%% weight (single oracle)");
        console.log("    14400,  // 4 hours staleness");
        console.log("    1500    // 15%% max deviation from TWAP");
        console.log("  );");
        
        console.log("\nMAANG ORACLE READY FOR DRI PROTOCOL INTEGRATION!");
    }
}
