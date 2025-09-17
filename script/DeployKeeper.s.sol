// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "forge-std/Script.sol";
import "../src/KeeperContract.sol";

contract DeployKeeper is Script {
    function run() external {
        uint256 deployerPrivateKey = vm.envUint("PRIVATE_KEY");
        vm.startBroadcast(deployerPrivateKey);

        // Deploy the keeper contract pointing to our WorkingPyth
        BattleProofKeeperContract keeper = new BattleProofKeeperContract(
            0x431904FE789A377d166eEFbaE1681239C17B134b // WorkingPyth address
        );

        console.log("Keeper deployed to:", address(keeper));

        vm.stopBroadcast();
    }
}