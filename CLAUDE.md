# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Foundry-based Solidity project that implements a MAANG (META, AAPL, AMZN, NVDA, GOOGL) stock price oracle system using Pyth Network price feeds. The system consists of smart contracts for price aggregation and a JavaScript keeper service for real-time price updates.

## Core Architecture

### Smart Contracts (`src/`)
- **IOracle.sol**: Standard oracle interface with `getPrice()`, `viewPrice()`, `isStale()`, and `getDecimals()` methods
- **MAANGPythOracle.sol**: Main oracle contract that aggregates MAANG stock prices into a weighted index (20% each)
- **PythOracleConsumer.sol**: Unified oracle consumer that implements IOracle interface for DRI Protocol compatibility
- **pyth/**: Contains Pyth Network integration contracts including AbstractPyth, MockPyth, and PythAggregatorV3

### Key Design Patterns
- Contracts use 18-decimal precision for price data
- MAANG oracle uses equal weighting (20% each stock)
- Price staleness detection with configurable max age
- Minimum valid feeds requirement for aggregation
- Event emission for price updates and status changes

### Keeper Service
- **production-keeper-sse.js**: Production-ready SSE-based keeper with WebSocket RPC connectivity
- Real-time SSE streaming from Hermes API (~400ms price updates)
- WebSocket RPC connection for better reliability and lower latency
- Intelligent debouncing and price change detection
- Comprehensive monitoring, health checks, and auto-reconnection logic
- **production-keeper.js**: Legacy polling-based keeper (5-second intervals)

## Development Commands

### Foundry (Smart Contracts)
```bash
forge build                    # Compile contracts
forge test                     # Run tests
forge test -vvv               # Run tests with verbose output
forge script <script_name>    # Run deployment scripts
```

### JavaScript (Keeper)
```bash
node production-keeper.js     # Run the production keeper
npm test                      # Run tests (currently not configured)
```

## Feed IDs (Pyth Network)
- META/USD: `0x78a3e3b8e676a8f73c439f5d749737034b139bbbe899ba5775216fba596607fe`
- AAPL/USD: `0x49f6b65cb1de6b10eaf75e7c03ca029c306d0357e91b5311b175084a5ad55688`
- AMZN/USD: `0xb5d0e0fa58a1f8b81498ae670ce93c872d14434b72c364885d4fa1b257cbb07a`
- NVDA/USD: `0xb1073854ed24cbc755dc527418f52b7d271f6cc967bbf8d8129112b18860a593`
- GOOGL/USD: `0x5a48c03e9b9cb337801073ed9d166817473697efff0d138874e0f6a33d6d5aa6`

## Configuration

### Environment Variables
- `PRIVATE_KEY`: Private key for wallet transactions
- `RPC_URL`: ETO testnet WebSocket URL (default: wss://testnet-eto-y246d.avax-test.network/ext/bc/2hpQwDpDGEa4915WnAp6MP7qCcoP35jqUHFji7p3o9E99UBJmk/ws?token=...)
- `SNOWTRACE_API_KEY`: For contract verification on Snowtrace

### Network Configuration (foundry.toml)
- Target: ETO testnet
- Uses environment variables for RPC URL and Snowtrace API key
- Standard Foundry project structure with `src/`, `out/`, `lib/` directories

## Deployment

Deployment scripts are located in `script/` directory. The AWS deployment guide (`AWS_DEPLOYMENT.md`) provides detailed instructions for production deployment including:
- EC2 instance setup
- PM2 process management for keeper
- Nginx reverse proxy configuration
- Dashboard setup and monitoring

## Key Implementation Notes

- MAANGPythOracle contract address: `0x36df4CF7cB10eD741Ed6EC553365cf515bc07121`
- All prices are scaled to 18 decimals for consistency
- Keeper uses nonce management to prevent transaction conflicts
- Health monitoring includes balance checks, feed validation, and performance metrics
- Contracts implement comprehensive error handling and validation