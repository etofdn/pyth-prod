// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Script.sol";
import "../src/WorkingPyth.sol";
import "../src/WorkingPriceConsumer.sol";
import "../src/oracles/MAANGPythOracle.sol";
import "../src/KeeperContract.sol";

contract DeployFullMAANGSystem is Script {
    function run() external {
        uint256 deployerPrivateKey = vm.envUint("PRIVATE_KEY");
        vm.startBroadcast(deployerPrivateKey);

        console.log("=== DEPLOYING FULL MAANG SYSTEM TO ETO TESTNET ===");
        console.log("Deployer address:", vm.addr(deployerPrivateKey));

        // 1. Deploy WorkingPyth (if not already deployed)
        address existingPythAddress = 0x431904FE789A377d166eEFbaE1681239C17B134b;
        console.log("Using existing WorkingPyth at:", existingPythAddress);

        // 2. Deploy WorkingPriceConsumer (if not already deployed)
        address existingConsumerAddress = 0x0000000000000000000000000000000000000000; // Update with actual address
        console.log("Using existing WorkingPriceConsumer at:", existingConsumerAddress);

        // 3. Deploy MAANG Oracle
        console.log("\n=== DEPLOYING MAANG ORACLE ===");
        MAANGPythOracle maangOracle = new MAANGPythOracle(
            existingPythAddress,
            14400,  // 4 hours max age for stocks
            3       // Need at least 3 out of 5 stocks
        );
        console.log("MAANG Oracle deployed at:", address(maangOracle));

        // 4. Deploy Keeper Contract
        console.log("\n=== DEPLOYING KEEPER CONTRACT ===");
        BattleProofKeeperContract keeper = new BattleProofKeeperContract(existingPythAddress);
        console.log("Keeper Contract deployed at:", address(keeper));

        // 5. Test the system
        console.log("\n=== TESTING SYSTEM INTEGRATION ===");
        
        // Test MAANG oracle
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
            console.log("Human readable price: $%s", price / 1e13);
        } catch {
            console.log("Failed to get price (expected - no real data yet)");
        }

        try maangOracle.isStale() returns (bool stale) {
            console.log("Is Stale:", stale);
        } catch {
            console.log("Failed to check staleness");
        }

        // Test keeper
        try keeper.getKeeperStats() returns (
            uint256 lastUpdateTime,
            uint256 totalUpdates,
            uint256 failedUpdates,
            uint256 timeSinceLastUpdate,
            bool emergencyNeeded
        ) {
            console.log("\nKeeper Stats:");
            console.log("Last Update:", lastUpdateTime);
            console.log("Total Updates:", totalUpdates);
            console.log("Failed Updates:", failedUpdates);
            console.log("Time Since Last Update:", timeSinceLastUpdate);
            console.log("Emergency Needed:", emergencyNeeded);
        } catch {
            console.log("Failed to get keeper stats");
        }

        vm.stopBroadcast();

        console.log("\n=== FULL MAANG SYSTEM DEPLOYMENT COMPLETE ===");
        console.log("WorkingPyth:", existingPythAddress);
        console.log("WorkingPriceConsumer:", existingConsumerAddress);
        console.log("MAANG Oracle:", address(maangOracle));
        console.log("Keeper Contract:", address(keeper));
        
        console.log("\n=== INTEGRATION INSTRUCTIONS ===");
        console.log("1. Fund the keeper contract with AVAX for update fees");
        console.log("2. Start the keeper polling system");
        console.log("3. Monitor MAANG oracle for price updates");
        console.log("4. Integrate with OracleAggregator when ready");
        
        console.log("\n=== NEXT STEPS ===");
        console.log("Run: node maang-integration.js");
        console.log("This will start the full MAANG monitoring system");
    }
}
