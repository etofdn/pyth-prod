// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "./pyth/PythStructs.sol";

/**
 * @title WorkingPyth
 * @notice A working Pyth implementation that accepts real VAAs - fuck the interfaces
 */
contract WorkingPyth {
    mapping(bytes32 => PythStructs.PriceFeed) private priceFeeds;

    uint256 public constant SINGLE_UPDATE_FEE = 1 wei;

    event PriceFeedUpdate(
        bytes32 indexed id,
        uint64 publishTime,
        int64 price,
        uint64 conf
    );

    function updatePriceFeeds(bytes[] calldata updateData) external payable {
        uint256 requiredFee = SINGLE_UPDATE_FEE * updateData.length;
        require(msg.value >= requiredFee, "Insufficient fee");

        for (uint i = 0; i < updateData.length; i++) {
            _processVAA(updateData[i]);
        }
    }

    function _processVAA(bytes calldata vaa) internal {
        // Basic VAA validation
        require(vaa.length >= 100, "Invalid VAA length");

        // VAA starts with "PNAU" signature for Pyth
        require(
            vaa[0] == 0x50 && // P
            vaa[1] == 0x4e && // N
            vaa[2] == 0x41 && // A
            vaa[3] == 0x55,   // U
            "Invalid VAA signature"
        );

        // For testnet, we'll extract basic price data
        // This is simplified - real implementation would do full Wormhole verification
        _parseBasicPriceData(vaa);
    }

    function _parseBasicPriceData(bytes calldata vaa) internal {
        // Simplified parsing - extract price ID and data from known positions
        // This is for testnet only - real implementation needs full VAA parsing

        // Look for price data pattern in VAA
        for (uint i = 100; i < vaa.length - 100; i += 32) {
            if (i + 96 <= vaa.length) {
                bytes32 possiblePriceId = bytes32(vaa[i:i+32]);

                // Check if this looks like a valid price ID (not all zeros)
                if (possiblePriceId != bytes32(0)) {
                    // Extract price components (simplified)
                    int64 price = int64(uint64(bytes8(vaa[i+32:i+40])));
                    uint64 conf = uint64(bytes8(vaa[i+40:i+48]));
                    int32 expo = int32(uint32(bytes4(vaa[i+48:i+52])));
                    uint64 publishTime = uint64(block.timestamp);

                    if (price > 0) {
                        _storePriceFeed(possiblePriceId, price, conf, expo, publishTime);
                        break; // Found and stored one price, that's enough for this VAA
                    }
                }
            }
        }
    }

    function _storePriceFeed(
        bytes32 priceId,
        int64 price,
        uint64 conf,
        int32 expo,
        uint64 publishTime
    ) internal {
        priceFeeds[priceId] = PythStructs.PriceFeed({
            id: priceId,
            price: PythStructs.Price({
                price: price,
                conf: conf,
                expo: expo,
                publishTime: publishTime
            }),
            emaPrice: PythStructs.Price({
                price: price,
                conf: conf,
                expo: expo,
                publishTime: publishTime
            })
        });

        emit PriceFeedUpdate(priceId, publishTime, price, conf);
    }

    function getUpdateFee(bytes[] calldata updateData) external pure returns (uint) {
        return SINGLE_UPDATE_FEE * updateData.length;
    }

    function getPriceUnsafe(bytes32 id) external view returns (PythStructs.Price memory) {
        require(priceFeeds[id].price.publishTime > 0, "Price feed not found");
        return priceFeeds[id].price;
    }

    function getLatestPrice(bytes32 id) external view returns (int64, uint256) {
        require(priceFeeds[id].price.publishTime > 0, "Price feed not found");
        return (priceFeeds[id].price.price, priceFeeds[id].price.publishTime);
    }

    // Emergency function to set test prices
    function setTestPrice(
        bytes32 id,
        int64 price,
        uint64 conf,
        int32 expo
    ) external {
        _storePriceFeed(id, price, conf, expo, uint64(block.timestamp));
    }

    // Function to check if price feed exists
    function priceFeedExists(bytes32 id) external view returns (bool) {
        return priceFeeds[id].price.publishTime > 0;
    }
}