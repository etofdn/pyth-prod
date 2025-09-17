// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "forge-std/Script.sol";
import "../src/PythDeployment.sol";
import "../src/PythPriceConsumer.sol";

contract DeployPyth is Script {
    function run() external {
        uint256 deployerPrivateKey = vm.envUint("PRIVATE_KEY");
        vm.startBroadcast(deployerPrivateKey);

        console.log("Deploying Pyth contracts to ETO Testnet...");
        console.log("Deployer address:", vm.addr(deployerPrivateKey));

        // Deploy MockPyth for testnet
        PythDeployment pythDeployment = new PythDeployment();
        address pythAddress = pythDeployment.getPythAddress();

        console.log("MockPyth deployed at:", pythAddress);
        console.log("PythDeployment contract deployed at:", address(pythDeployment));

        // Deploy price consumer contract
        PythPriceConsumer priceConsumer = new PythPriceConsumer(pythAddress);
        console.log("PythPriceConsumer deployed at:", address(priceConsumer));

        // Log price feed IDs for reference
        console.log("=== Price Feed IDs ===");
        console.log("META/USD:", vm.toString(priceConsumer.META_USD_FEED_ID()));
        console.log("AAPL/USD:", vm.toString(priceConsumer.AAPL_USD_FEED_ID()));
        console.log("AMZN/USD:", vm.toString(priceConsumer.AMZN_USD_FEED_ID()));
        console.log("NVDA/USD:", vm.toString(priceConsumer.NVDA_USD_FEED_ID()));
        console.log("GOOGL/USD:", vm.toString(priceConsumer.GOOGL_USD_FEED_ID()));

        vm.stopBroadcast();

        // Save deployment addresses to file
        string memory deploymentInfo = string.concat(
            "ETO Testnet Pyth Deployment\n",
            "==========================\n",
            "MockPyth: ", vm.toString(pythAddress), "\n",
            "PythDeployment: ", vm.toString(address(pythDeployment)), "\n",
            "PythPriceConsumer: ", vm.toString(address(priceConsumer)), "\n",
            "Deployer: ", vm.toString(vm.addr(deployerPrivateKey)), "\n",
            "\nPrice Feed IDs:\n",
            "META/USD: ", vm.toString(priceConsumer.META_USD_FEED_ID()), "\n",
            "AAPL/USD: ", vm.toString(priceConsumer.AAPL_USD_FEED_ID()), "\n",
            "AMZN/USD: ", vm.toString(priceConsumer.AMZN_USD_FEED_ID()), "\n",
            "NVDA/USD: ", vm.toString(priceConsumer.NVDA_USD_FEED_ID()), "\n",
            "GOOGL/USD: ", vm.toString(priceConsumer.GOOGL_USD_FEED_ID()), "\n"
        );


    }
}