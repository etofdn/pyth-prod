// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

interface IPyth {
    function updatePriceFeeds(bytes[] calldata updateData) external payable;
    function getUpdateFee(bytes[] calldata updateData) external view returns (uint256);
}

contract BattleProofKeeperContract {
    IPyth public immutable pyth;
    address public owner;
    address public keeper;

    uint256 public constant MAX_UPDATE_DELAY = 60; // 1 minute max delay
    uint256 public lastUpdateTime;
    uint256 public totalUpdates;
    uint256 public failedUpdates;

    mapping(address => bool) public authorizedKeepers;
    mapping(bytes32 => uint256) public lastPriceUpdate;

    event PriceUpdated(bytes32[] priceIds, uint256 timestamp, uint256 updateCount);
    event KeeperAdded(address keeper);
    event KeeperRemoved(address keeper);
    event EmergencyUpdate(bytes32[] priceIds, address caller);

    modifier onlyOwner() {
        require(msg.sender == owner, "Not owner");
        _;
    }

    modifier onlyKeeper() {
        require(authorizedKeepers[msg.sender] || msg.sender == owner, "Not authorized keeper");
        _;
    }

    constructor(address _pyth) {
        pyth = IPyth(_pyth);
        owner = msg.sender;
        authorizedKeepers[msg.sender] = true;
        lastUpdateTime = block.timestamp;
    }

    function updatePricesInstant(bytes[] calldata updateData) external payable onlyKeeper {
        require(updateData.length > 0, "No update data");
        require(block.timestamp <= lastUpdateTime + MAX_UPDATE_DELAY || msg.sender == owner, "Update too frequent");

        uint256 fee = pyth.getUpdateFee(updateData);
        require(msg.value >= fee, "Insufficient fee");

        try pyth.updatePriceFeeds{value: fee}(updateData) {
            lastUpdateTime = block.timestamp;
            totalUpdates++;

            // Extract price IDs for event (simplified)
            bytes32[] memory priceIds = new bytes32[](updateData.length);
            for (uint i = 0; i < updateData.length; i++) {
                priceIds[i] = keccak256(updateData[i]);
                lastPriceUpdate[priceIds[i]] = block.timestamp;
            }

            emit PriceUpdated(priceIds, block.timestamp, totalUpdates);

            // Refund excess
            if (msg.value > fee) {
                payable(msg.sender).transfer(msg.value - fee);
            }

        } catch {
            failedUpdates++;
            revert("Price update failed");
        }
    }

    function emergencyUpdate(bytes[] calldata updateData) external payable {
        require(block.timestamp > lastUpdateTime + MAX_UPDATE_DELAY, "Emergency not needed");
        require(updateData.length > 0, "No update data");

        uint256 fee = pyth.getUpdateFee(updateData);
        require(msg.value >= fee, "Insufficient fee");

        pyth.updatePriceFeeds{value: fee}(updateData);

        lastUpdateTime = block.timestamp;
        totalUpdates++;

        bytes32[] memory priceIds = new bytes32[](updateData.length);
        for (uint i = 0; i < updateData.length; i++) {
            priceIds[i] = keccak256(updateData[i]);
            lastPriceUpdate[priceIds[i]] = block.timestamp;
        }

        emit EmergencyUpdate(priceIds, msg.sender);

        if (msg.value > fee) {
            payable(msg.sender).transfer(msg.value - fee);
        }
    }

    function addKeeper(address _keeper) external onlyOwner {
        authorizedKeepers[_keeper] = true;
        emit KeeperAdded(_keeper);
    }

    function removeKeeper(address _keeper) external onlyOwner {
        authorizedKeepers[_keeper] = false;
        emit KeeperRemoved(_keeper);
    }

    function getKeeperStats() external view returns (
        uint256 _lastUpdateTime,
        uint256 _totalUpdates,
        uint256 _failedUpdates,
        uint256 _timeSinceLastUpdate,
        bool _emergencyNeeded
    ) {
        _lastUpdateTime = lastUpdateTime;
        _totalUpdates = totalUpdates;
        _failedUpdates = failedUpdates;
        _timeSinceLastUpdate = block.timestamp - lastUpdateTime;
        _emergencyNeeded = _timeSinceLastUpdate > MAX_UPDATE_DELAY;
    }

    function fundKeeper() external payable {
        // Allow anyone to fund the keeper contract
    }

    function withdrawFunds(uint256 amount) external onlyOwner {
        require(amount <= address(this).balance, "Insufficient balance");
        payable(owner).transfer(amount);
    }

    receive() external payable {}
}