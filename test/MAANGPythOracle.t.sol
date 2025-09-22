// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Test.sol";
import "../src/oracles/MAANGPythOracle.sol";
import "../src/WorkingPyth.sol";
import "../src/interfaces/IOracle.sol";

contract MAANGPythOracleTest is Test {
    MAANGPythOracle public maangOracle;
    WorkingPyth public workingPyth;
    
    address public deployer;
    uint256 public maxAge = 14400; // 4 hours
    uint256 public minValidFeeds = 3;
    
    // Price feed IDs
    bytes32 public constant META_FEED_ID = 0x78a3e3b8e676a8f73c439f5d749737034b139bbbe899ba5775216fba596607fe;
    bytes32 public constant AAPL_FEED_ID = 0x49f6b65cb1de6b10eaf75e7c03ca029c306d0357e91b5311b175084a5ad55688;
    bytes32 public constant AMZN_FEED_ID = 0xb5d0e0fa58a1f8b81498ae670ce93c872d14434b72c364885d4fa1b257cbb07a;
    bytes32 public constant NVDA_FEED_ID = 0xb1073854ed24cbc755dc527418f52b7d271f6cc967bbf8d8129112b18860a593;
    bytes32 public constant GOOGL_FEED_ID = 0x5a48c03e9b9cb337801073ed9d166817473697efff0d138874e0f6a33d6d5aa6;

    function setUp() public {
        deployer = address(this);
        
        // Deploy WorkingPyth
        workingPyth = new WorkingPyth();
        
        // Deploy MAANG Oracle
        maangOracle = new MAANGPythOracle(
            address(workingPyth),
            maxAge,
            minValidFeeds
        );
        
        // Set test prices for all MAANG stocks
        _setTestPrices();
    }

    function _setTestPrices() internal {
        // Set realistic test prices (in 5 decimals)
        workingPyth.setTestPrice(META_FEED_ID, 778 * 10**5, 10 * 10**5, -5);  // $778
        workingPyth.setTestPrice(AAPL_FEED_ID, 238 * 10**5, 5 * 10**5, -5);   // $238
        workingPyth.setTestPrice(AMZN_FEED_ID, 220 * 10**5, 5 * 10**5, -5);   // $220
        workingPyth.setTestPrice(NVDA_FEED_ID, 175 * 10**5, 5 * 10**5, -5);   // $175
        workingPyth.setTestPrice(GOOGL_FEED_ID, 190 * 10**5, 5 * 10**5, -5);  // $190
    }

    // ===== BASIC FUNCTIONALITY TESTS =====

    function test_GetPriceReturns18Decimals() public {
        (uint256 price, uint256 timestamp) = maangOracle.viewPrice();
        
        // Price should be in 18 decimals
        assertTrue(price > 0, "Price should be positive");
        assertTrue(timestamp > 0, "Timestamp should be positive");
        
        // Verify it's scaled to 18 decimals (should be much larger than original)
        assertTrue(price > 778 * 10**5, "Price should be scaled to 18 decimals");
    }

    function test_ViewPriceMatchesGetPrice() public {
        (uint256 viewPrice, uint256 viewTimestamp) = maangOracle.viewPrice();
        (uint256 getPrice, uint256 getTimestamp) = maangOracle.getPrice();
        
        assertEq(viewPrice, getPrice, "View price should match get price");
        assertEq(viewTimestamp, getTimestamp, "Timestamps should match");
    }

    function test_IsStaleDetectsOldData() public {
        // Initially should not be stale
        assertFalse(maangOracle.isStale(), "Fresh prices should not be stale");
        
        // Fast forward time beyond maxAge
        vm.warp(block.timestamp + maxAge + 1);
        
        // Should now be stale (insufficient valid feeds)
        assertTrue(maangOracle.isStale(), "Old prices should be stale");
    }

    function test_GetDecimals() public {
        assertEq(maangOracle.getDecimals(), 5, "Should return 5 decimals");
    }

    function test_GetAssetName() public {
        assertEq(maangOracle.getAssetName(), "MAANG/USD", "Should return correct asset name");
    }

    function test_GetTotalWeight() public {
        assertEq(maangOracle.getTotalWeight(), 10000, "Total weight should be 10000 (100%)");
    }

    // ===== MAANG INDEX CALCULATION TESTS =====

    function test_MAANGIndexCalculation() public {
        (uint256 indexPrice, uint256 timestamp) = maangOracle.viewPrice();
        
        // Expected calculation: (778 + 238 + 220 + 175 + 190) / 5 = 320.2
        // Scaled to 18 decimals: 320.2 * 1e13 = 320200000000000000000
        uint256 expectedPrice = 320200000000000000000; // Approximately
        
        // Allow some tolerance due to rounding
        assertApproxEqRel(indexPrice, expectedPrice, 1e15, "Index price should be approximately correct");
        assertTrue(timestamp > 0, "Timestamp should be positive");
    }

    function test_MAANGBreakdown() public {
        (
            bytes32[] memory feedIds,
            uint256[] memory prices,
            uint256[] memory timestamps,
            bool[] memory isValid,
            string[] memory symbols
        ) = maangOracle.getMAANGBreakdown();
        
        assertEq(feedIds.length, 5, "Should have 5 feed IDs");
        assertEq(symbols.length, 5, "Should have 5 symbols");
        
        // Check symbols
        assertEq(symbols[0], "META", "First symbol should be META");
        assertEq(symbols[1], "AAPL", "Second symbol should be AAPL");
        assertEq(symbols[2], "AMZN", "Third symbol should be AMZN");
        assertEq(symbols[3], "NVDA", "Fourth symbol should be NVDA");
        assertEq(symbols[4], "GOOGL", "Fifth symbol should be GOOGL");
        
        // All should be valid initially
        for (uint256 i = 0; i < 5; i++) {
            assertTrue(isValid[i], string(abi.encodePacked("Feed ", symbols[i], " should be valid")));
            assertTrue(prices[i] > 0, string(abi.encodePacked("Price for ", symbols[i], " should be positive")));
        }
    }

    // ===== ERROR HANDLING TESTS =====

    function test_RevertsOnInsufficientValidFeeds() public {
        // Set prices to 0 for 3 feeds (only 2 valid)
        workingPyth.setTestPrice(META_FEED_ID, 0, 0, -5);
        workingPyth.setTestPrice(AAPL_FEED_ID, 0, 0, -5);
        workingPyth.setTestPrice(AMZN_FEED_ID, 0, 0, -5);
        
        vm.expectRevert(abi.encodeWithSelector(MAANGPythOracle.InsufficientValidFeeds.selector, 2, 3));
        maangOracle.viewPrice();
    }

    function test_HandlesStaleData() public {
        // Fast forward time to make data stale
        vm.warp(block.timestamp + maxAge + 1);
        
        // Should revert due to insufficient valid feeds (all are stale)
        vm.expectRevert(abi.encodeWithSelector(MAANGPythOracle.InsufficientValidFeeds.selector, 0, 3));
        maangOracle.viewPrice();
    }

    function test_HandlesInvalidPrices() public {
        // Set negative prices
        workingPyth.setTestPrice(META_FEED_ID, -100 * 10**5, 10 * 10**5, -5);
        workingPyth.setTestPrice(AAPL_FEED_ID, -50 * 10**5, 5 * 10**5, -5);
        
        // Should still work with remaining valid feeds
        (uint256 price, uint256 timestamp) = maangOracle.viewPrice();
        assertTrue(price > 0, "Should still return valid price with some invalid feeds");
    }

    // ===== WEIGHT DISTRIBUTION TESTS =====

    function test_EqualWeightDistribution() public {
        assertEq(maangOracle.META_WEIGHT(), 2000, "META weight should be 20%");
        assertEq(maangOracle.AAPL_WEIGHT(), 2000, "AAPL weight should be 20%");
        assertEq(maangOracle.AMZN_WEIGHT(), 2000, "AMZN weight should be 20%");
        assertEq(maangOracle.NVDA_WEIGHT(), 2000, "NVDA weight should be 20%");
        assertEq(maangOracle.GOOGL_WEIGHT(), 2000, "GOOGL weight should be 20%");
    }

    // ===== INTEGRATION TESTS =====

    function test_IOracleInterfaceCompliance() public {
        // Test that all required functions exist and work
        maangOracle.getPrice();
        maangOracle.viewPrice();
        maangOracle.isStale();
        maangOracle.getDecimals();
    }

    function test_EventEmissions() public {
        // Test that getPrice emits events
        vm.expectEmit(true, true, true, true);
        emit MAANGPythOracle.MAANGIndexUpdated(320200000000000000000, block.timestamp, 5);
        
        maangOracle.getPrice();
    }

    // ===== EDGE CASES =====

    function test_WorksWithMinimumValidFeeds() public {
        // Set only 3 feeds to valid prices (minimum required)
        workingPyth.setTestPrice(META_FEED_ID, 778 * 10**5, 10 * 10**5, -5);
        workingPyth.setTestPrice(AAPL_FEED_ID, 238 * 10**5, 5 * 10**5, -5);
        workingPyth.setTestPrice(AMZN_FEED_ID, 220 * 10**5, 5 * 10**5, -5);
        workingPyth.setTestPrice(NVDA_FEED_ID, 0, 0, -5);  // Invalid
        workingPyth.setTestPrice(GOOGL_FEED_ID, 0, 0, -5); // Invalid
        
        (uint256 price, uint256 timestamp) = maangOracle.viewPrice();
        assertTrue(price > 0, "Should work with minimum valid feeds");
        assertTrue(timestamp > 0, "Should have valid timestamp");
    }

    function test_PriceScalingCorrect() public {
        // Test that prices are correctly scaled from 5 to 18 decimals
        (uint256 indexPrice,) = maangOracle.viewPrice();
        
        // Raw average: (778 + 238 + 220 + 175 + 190) / 5 = 320.2
        // Scaled: 320.2 * 1e13 = 320200000000000000000
        uint256 expectedPrice = 320200000000000000000;
        
        // Allow 1% tolerance
        assertApproxEqRel(indexPrice, expectedPrice, 1e16, "Price scaling should be correct");
    }

    function test_ConfigurationValues() public {
        assertEq(maangOracle.getMaxAge(), maxAge, "Max age should match constructor");
        assertEq(maangOracle.getMinValidFeeds(), minValidFeeds, "Min valid feeds should match constructor");
    }
}
