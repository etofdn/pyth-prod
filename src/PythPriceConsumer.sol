// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "./pyth/IPyth.sol";
import "./pyth/PythStructs.sol";

contract PythPriceConsumer {
    IPyth public pyth;

    // Price feed IDs from notes.txt
    bytes32 public constant META_USD_FEED_ID = 0x78a3e3b8e676a8f73c439f5d749737034b139bbbe899ba5775216fba596607fe;
    bytes32 public constant AAPL_USD_FEED_ID = 0x49f6b65cb1de6b10eaf75e7c03ca029c306d0357e91b5311b175084a5ad55688;
    bytes32 public constant AMZN_USD_FEED_ID = 0xb5d0e0fa58a1f8b81498ae670ce93c872d14434b72c364885d4fa1b257cbb07a;
    bytes32 public constant NVDA_USD_FEED_ID = 0xb1073854ed24cbc755dc527418f52b7d271f6cc967bbf8d8129112b18860a593;
    bytes32 public constant GOOGL_USD_FEED_ID = 0x5a48c03e9b9cb337801073ed9d166817473697efff0d138874e0f6a33d6d5aa6;

    event PriceUpdated(bytes32 indexed priceId, int64 price, uint32 timestamp);

    constructor(address _pythAddress) {
        pyth = IPyth(_pythAddress);
    }

    function updatePriceFeeds(bytes[] calldata updateData) external payable {
        uint fee = pyth.getUpdateFee(updateData);
        require(msg.value >= fee, "Insufficient fee for price update");

        pyth.updatePriceFeeds{value: fee}(updateData);

        // Emit events for updated prices
        for (uint i = 0; i < updateData.length; i++) {
            // This is a simplified approach - in practice you'd parse the VAA to get price IDs
            emit PriceUpdated(META_USD_FEED_ID, 0, uint32(block.timestamp));
        }
    }

    function getLatestPrice(bytes32 priceId) external view returns (int64, uint256) {
        PythStructs.Price memory price = pyth.getPriceUnsafe(priceId);
        return (price.price, price.publishTime);
    }

    function getLatestPriceWithStaleness(bytes32 priceId, uint staleness) external view returns (int64, uint256) {
        PythStructs.Price memory price = pyth.getPriceNoOlderThan(priceId, staleness);
        return (price.price, price.publishTime);
    }

    function getMetaPrice() external view returns (int64, uint256) {
        return this.getLatestPrice(META_USD_FEED_ID);
    }

    function getApplePrice() external view returns (int64, uint256) {
        return this.getLatestPrice(AAPL_USD_FEED_ID);
    }

    function getAmazonPrice() external view returns (int64, uint256) {
        return this.getLatestPrice(AMZN_USD_FEED_ID);
    }

    function getNvidiaPrice() external view returns (int64, uint256) {
        return this.getLatestPrice(NVDA_USD_FEED_ID);
    }

    function getGooglePrice() external view returns (int64, uint256) {
        return this.getLatestPrice(GOOGL_USD_FEED_ID);
    }

    function getUpdateFee(bytes[] calldata updateData) external view returns (uint) {
        return pyth.getUpdateFee(updateData);
    }
}