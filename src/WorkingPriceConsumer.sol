// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "./WorkingPyth.sol";

contract WorkingPriceConsumer {
    WorkingPyth public pyth;

    // Complete price feed IDs for all requested assets
    bytes32 public constant BTC_USD_FEED_ID = 0xe62df6c8b4a85fe1a67db44dc12de5db330f7ac66b72dc658afedf0f4a415b43;
    bytes32 public constant ETH_USD_FEED_ID = 0xff61491a931112ddf1bd8147cd1b641375f79f5825126d665480874634fd0ace;
    bytes32 public constant META_USD_FEED_ID = 0x78a3e3b8e676a8f73c439f5d749737034b139bbbe899ba5775216fba596607fe;
    bytes32 public constant AAPL_USD_FEED_ID = 0x49f6b65cb1de6b10eaf75e7c03ca029c306d0357e91b5311b175084a5ad55688;
    bytes32 public constant NVDA_USD_FEED_ID = 0xb1073854ed24cbc755dc527418f52b7d271f6cc967bbf8d8129112b18860a593;
    bytes32 public constant AMZN_USD_FEED_ID = 0xb5d0e0fa58a1f8b81498ae670ce93c872d14434b72c364885d4fa1b257cbb07a;
    bytes32 public constant GOOGL_USD_FEED_ID = 0x5a48c03e9b9cb337801073ed9d166817473697efff0d138874e0f6a33d6d5aa6;

    event PriceUpdated(bytes32 indexed priceId, int64 price, uint256 timestamp);

    constructor(address _pythAddress) {
        pyth = WorkingPyth(_pythAddress);
    }

    function updatePriceFeeds(bytes[] calldata updateData) external payable {
        uint fee = pyth.getUpdateFee(updateData);
        require(msg.value >= fee, "Insufficient fee for price update");

        pyth.updatePriceFeeds{value: fee}(updateData);

        // Emit events for updated prices
        emit PriceUpdated(BTC_USD_FEED_ID, 0, block.timestamp);
    }

    function getLatestPrice(bytes32 priceId) external view returns (int64, uint256) {
        return pyth.getLatestPrice(priceId);
    }

    function getBtcPrice() external view returns (int64, uint256) {
        return pyth.getLatestPrice(BTC_USD_FEED_ID);
    }

    function getEthPrice() external view returns (int64, uint256) {
        return pyth.getLatestPrice(ETH_USD_FEED_ID);
    }

    function getMetaPrice() external view returns (int64, uint256) {
        return pyth.getLatestPrice(META_USD_FEED_ID);
    }

    function getApplePrice() external view returns (int64, uint256) {
        return pyth.getLatestPrice(AAPL_USD_FEED_ID);
    }

    function getNvidiaPrice() external view returns (int64, uint256) {
        return pyth.getLatestPrice(NVDA_USD_FEED_ID);
    }

    function getAmazonPrice() external view returns (int64, uint256) {
        return pyth.getLatestPrice(AMZN_USD_FEED_ID);
    }

    function getGooglePrice() external view returns (int64, uint256) {
        return pyth.getLatestPrice(GOOGL_USD_FEED_ID);
    }

    function getUpdateFee(bytes[] calldata updateData) external view returns (uint) {
        return pyth.getUpdateFee(updateData);
    }

    function checkPriceFeedExists(bytes32 priceId) external view returns (bool) {
        return pyth.priceFeedExists(priceId);
    }
}