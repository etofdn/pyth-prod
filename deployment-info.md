# ETO Testnet Pyth Deployment

## Deployed Contracts

- **MockPyth**: `0xaB00f2e3974edF565ac742ea4aB21669E73e7517`
- **PythDeployment**: `0x789d526c2006a80b4542806Ba762a377cC8e73Cd`
- **PythPriceConsumer**: `0xBbc5ED6A9c8B9f8C4dC2ccd3fd06b9542eF7a02A`
- **WorkingPyth**: `0x431904FE789A377d166eEFbaE1681239C17B134b`
- **MAANGPythOracle**: `0x051d7E621F6022F845E81a6103A81df77C6d9b3f` ⭐ **NEW**
- **Deployer**: `0xa4e02339c313BF7Fc9e70D5E0C5c2BfEdF1B5327`

## Price Feed IDs

- **META/USD**: `0x78a3e3b8e676a8f73c439f5d749737034b139bbbe899ba5775216fba596607fe`
- **AAPL/USD**: `0x49f6b65cb1de6b10eaf75e7c03ca029c306d0357e91b5311b175084a5ad55688`
- **AMZN/USD**: `0xb5d0e0fa58a1f8b81498ae670ce93c872d14434b72c364885d4fa1b257cbb07a`
- **NVDA/USD**: `0xb1073854ed24cbc755dc527418f52b7d271f6cc967bbf8d8129112b18860a593`
- **GOOGL/USD**: `0x5a48c03e9b9cb337801073ed9d166817473697efff0d138874e0f6a33d6d5aa6`

## Network Details

- **RPC URL**: `https://testnet-eto-y246d.avax-test.network/ext/bc/2hpQwDpDGEa4915WnAp6MP7qCcoP35jqUHFji7p3o9E99UBJmk/rpc?token=da37bf16c0a88bb35f2e5c48bc8ce1229913fb135de21d7769a02b21f6c2b0ce`
- **Network Name**: ETO Testnet

## MAANG Oracle Configuration

- **Contract Address**: `0x051d7E621F6022F845E81a6103A81df77C6d9b3f`
- **Max Age**: 14400 seconds (4 hours)
- **Min Valid Feeds**: 3 out of 5 stocks required
- **Weight Distribution**: Equal weight (20% each for META, AAPL, AMZN, NVDA, GOOGL)
- **Total Weight**: 10000 (100%)
- **Decimals**: 5 (source) → 18 (scaled)

## Usage

Your MockPyth contract is now deployed and ready for testing. Use the PythPriceConsumer contract to interact with price feeds.

### MAANG Oracle Integration
```solidity
// For OracleAggregator integration:
aggregator.addOracleAdvanced(
    address(0x051d7E621F6022F845E81a6103A81df77C6d9b3f), // MAANG Oracle
    10000,  // 100% weight (single oracle)
    14400,  // 4 hours staleness
    1500    // 15% max deviation from TWAP
);
```