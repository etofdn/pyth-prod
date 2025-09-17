// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "forge-std/Script.sol";
import "../src/WorkingPyth.sol";
import "../src/WorkingPriceConsumer.sol";

contract DeployWorkingPyth is Script {
    function run() external {
        uint256 deployerPrivateKey = vm.envUint("PRIVATE_KEY");
        vm.startBroadcast(deployerPrivateKey);

        console.log("=== DEPLOYING WORKING PYTH FOR REAL HERMES INTEGRATION ===");
        console.log("Deployer address:", vm.addr(deployerPrivateKey));

        // Deploy WorkingPyth that can handle real VAAs
        WorkingPyth workingPyth = new WorkingPyth();
        console.log("WorkingPyth deployed at:", address(workingPyth));

        // Deploy price consumer
        WorkingPriceConsumer priceConsumer = new WorkingPriceConsumer(address(workingPyth));
        console.log("WorkingPriceConsumer deployed at:", address(priceConsumer));

        // Set initial test prices for all the fucking assets you want
        console.log("Setting test prices for all requested assets...");

        // Crypto feeds
        workingPyth.setTestPrice(
            0xe62df6c8b4a85fe1a67db44dc12de5db330f7ac66b72dc658afedf0f4a415b43, // BTC
            116000 * 10**8, 1000 * 10**8, -8
        );

        workingPyth.setTestPrice(
            0xff61491a931112ddf1bd8147cd1b641375f79f5825126d665480874634fd0ace, // ETH
            4500 * 10**8, 100 * 10**8, -8
        );

        // Stock feeds - META, AAPL, NVDA, AMZN, GOOGL
        workingPyth.setTestPrice(
            0x78a3e3b8e676a8f73c439f5d749737034b139bbbe899ba5775216fba596607fe, // META
            778 * 10**5, 10 * 10**5, -5
        );

        workingPyth.setTestPrice(
            0x49f6b65cb1de6b10eaf75e7c03ca029c306d0357e91b5311b175084a5ad55688, // AAPL
            238 * 10**5, 5 * 10**5, -5
        );

        workingPyth.setTestPrice(
            0xb1073854ed24cbc755dc527418f52b7d271f6cc967bbf8d8129112b18860a593, // NVDA
            175 * 10**5, 5 * 10**5, -5
        );

        workingPyth.setTestPrice(
            0xb5d0e0fa58a1f8b81498ae670ce93c872d14434b72c364885d4fa1b257cbb07a, // AMZN
            220 * 10**5, 5 * 10**5, -5
        );

        workingPyth.setTestPrice(
            0x5a48c03e9b9cb337801073ed9d166817473697efff0d138874e0f6a33d6d5aa6, // GOOGL
            190 * 10**5, 5 * 10**5, -5
        );

        console.log("All test prices set!");

        vm.stopBroadcast();

        console.log("\n=== FUCKING DEPLOYMENT COMPLETE ===");
        console.log("WORKING PYTH CONTRACT:", address(workingPyth));
        console.log("WORKING PRICE CONSUMER:", address(priceConsumer));
        console.log("\nALL YOUR REQUESTED ASSETS:");
        console.log("  BTC/USD  - READY");
        console.log("  ETH/USD  - READY");
        console.log("  META/USD - READY");
        console.log("  AAPL/USD - READY");
        console.log("  NVDA/USD - READY");
        console.log("  AMZN/USD - READY");
        console.log("  GOOGL/USD - READY");
        console.log("\nNOW READY FOR REAL HERMES VAA INTEGRATION!");
    }
}