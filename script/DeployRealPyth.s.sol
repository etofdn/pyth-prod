// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "forge-std/Script.sol";
import "../src/SimplePyth.sol";
import "../src/PythPriceConsumer.sol";

contract DeployRealPyth is Script {
    function run() external {
        uint256 deployerPrivateKey = vm.envUint("PRIVATE_KEY");
        vm.startBroadcast(deployerPrivateKey);

        console.log("=== DEPLOYING REAL PYTH FOR HERMES INTEGRATION ===");
        console.log("Deployer address:", vm.addr(deployerPrivateKey));

        // Deploy SimplePyth that can handle real VAAs
        SimplePyth realPyth = new SimplePyth();
        console.log("SimplePyth deployed at:", address(realPyth));

        // Deploy new price consumer with real Pyth
        PythPriceConsumer newPriceConsumer = new PythPriceConsumer(address(realPyth));
        console.log("New PythPriceConsumer deployed at:", address(newPriceConsumer));

        // Set test prices for immediate verification
        console.log("Setting test prices for all feeds...");

        // Crypto feeds
        bytes32 btcId = 0xe62df6c8b4a85fe1a67db44dc12de5db330f7ac66b72dc658afedf0f4a415b43;
        realPyth.setTestPrice(btcId, 116000 * 10**8, 1000 * 10**8, -8);

        bytes32 ethId = 0xff61491a931112ddf1bd8147cd1b641375f79f5825126d665480874634fd0ace;
        realPyth.setTestPrice(ethId, 4500 * 10**8, 100 * 10**8, -8);

        // Stock feeds
        bytes32 metaId = 0x78a3e3b8e676a8f73c439f5d749737034b139bbbe899ba5775216fba596607fe;
        realPyth.setTestPrice(metaId, 778 * 10**5, 10 * 10**5, -5);

        bytes32 aaplId = 0x49f6b65cb1de6b10eaf75e7c03ca029c306d0357e91b5311b175084a5ad55688;
        realPyth.setTestPrice(aaplId, 238 * 10**5, 5 * 10**5, -5);

        bytes32 nvdaId = 0xb1073854ed24cbc755dc527418f52b7d271f6cc967bbf8d8129112b18860a593;
        realPyth.setTestPrice(nvdaId, 175 * 10**5, 5 * 10**5, -5);

        bytes32 amznId = 0xb5d0e0fa58a1f8b81498ae670ce93c872d14434b72c364885d4fa1b257cbb07a;
        realPyth.setTestPrice(amznId, 220 * 10**5, 5 * 10**5, -5);

        bytes32 googlId = 0x5a48c03e9b9cb337801073ed9d166817473697efff0d138874e0f6a33d6d5aa6;
        realPyth.setTestPrice(googlId, 190 * 10**5, 5 * 10**5, -5);

        console.log("Test prices set for all feeds");

        vm.stopBroadcast();

        console.log("\n=== DEPLOYMENT COMPLETE ===");
        console.log("REAL PYTH CONTRACT:", address(realPyth));
        console.log("NEW PRICE CONSUMER:", address(newPriceConsumer));
        console.log("\nSupported Assets:");
        console.log("   BTC/USD");
        console.log("   ETH/USD");
        console.log("   META/USD");
        console.log("   AAPL/USD");
        console.log("   NVDA/USD");
        console.log("   AMZN/USD");
        console.log("   GOOGL/USD");
        console.log("\nREADY FOR REAL HERMES VAA INTEGRATION!");
    }
}