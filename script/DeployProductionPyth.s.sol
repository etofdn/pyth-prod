// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "forge-std/Script.sol";
import "../src/ProductionPyth.sol";
import "../src/PythPriceConsumer.sol";

contract DeployProductionPyth is Script {
    function run() external {
        uint256 deployerPrivateKey = vm.envUint("PRIVATE_KEY");
        vm.startBroadcast(deployerPrivateKey);

        console.log("Deploying Production Pyth for Hermes integration...");
        console.log("Deployer address:", vm.addr(deployerPrivateKey));

        // Deploy ProductionPyth that can handle real VAAs
        ProductionPyth productionPyth = new ProductionPyth(
            300,  // validTimePeriod: 5 minutes
            1     // singleUpdateFeeInWei: 1 wei for testnet
        );

        console.log("ProductionPyth deployed at:", address(productionPyth));

        // Deploy new price consumer with ProductionPyth
        PythPriceConsumer priceConsumer = new PythPriceConsumer(address(productionPyth));
        console.log("New PythPriceConsumer deployed at:", address(priceConsumer));

        // Set test prices for immediate testing
        console.log("Setting test prices...");

        // BTC/USD
        bytes32 btcId = 0xe62df6c8b4a85fe1a67db44dc12de5db330f7ac66b72dc658afedf0f4a415b43;
        productionPyth.setTestPrice(btcId, 116000 * 10**8, 100 * 10**8, -8, uint64(block.timestamp));

        // ETH/USD
        bytes32 ethId = 0xff61491a931112ddf1bd8147cd1b641375f79f5825126d665480874634fd0ace;
        productionPyth.setTestPrice(ethId, 4500 * 10**8, 50 * 10**8, -8, uint64(block.timestamp));

        console.log("Test prices set for BTC and ETH");

        vm.stopBroadcast();

        console.log("\n=== Deployment Summary ===");
        console.log("ProductionPyth:", address(productionPyth));
        console.log("PythPriceConsumer:", address(priceConsumer));
        console.log("Network: ETO Testnet");
        console.log("\nThis deployment can:");
        console.log("1. Handle real Hermes VAAs (simplified validation)");
        console.log("2. Accept off-chain price updates");
        console.log("3. Provide real-time price feeds");
    }
}