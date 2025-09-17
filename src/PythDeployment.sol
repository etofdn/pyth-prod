// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "./pyth/IPyth.sol";
import "./pyth/MockPyth.sol";

contract PythDeployment {
    MockPyth public immutable pyth;

    constructor() {
        // Deploy MockPyth for testnet use
        // validTimePeriod: 300 seconds (5 minutes)
        // singleUpdateFeeInWei: 1 wei (minimal fee for testnet)
        pyth = new MockPyth(300, 1);
    }

    function getPythAddress() external view returns (address) {
        return address(pyth);
    }
}