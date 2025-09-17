# Production-ready Oracle Keeper for 500M+ TVL protocols
FROM node:20-alpine AS builder

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci --only=production && npm cache clean --force

# Production stage
FROM node:20-alpine

# Add security and monitoring packages
RUN apk add --no-cache \
    curl \
    dumb-init \
    tini \
    && addgroup -g 1001 -S oracle \
    && adduser -S -D -H -u 1001 -s /sbin/nologin oracle

WORKDIR /app

# Copy dependencies from builder
COPY --from=builder /app/node_modules ./node_modules
COPY --chown=oracle:oracle keeper-polling.js ./
COPY --chown=oracle:oracle package.json ./

# Health check script
COPY --chown=oracle:oracle <<'EOF' /app/healthcheck.js
const https = require('https');
const { ethers } = require('ethers');

async function healthCheck() {
    try {
        // Check RPC connectivity
        const provider = new ethers.JsonRpcProvider(process.env.RPC_URL);
        const blockNumber = await provider.getBlockNumber();

        // Check Hermes API
        const req = https.get('https://hermes.pyth.network/v2/updates/price/latest?ids[]=78a3e3b8e676a8f73c439f5d749737034b139bbbe899ba5775216fba596607fe', (res) => {
            if (res.statusCode === 200) {
                console.log('✅ Health check passed');
                process.exit(0);
            } else {
                console.log('❌ Hermes API unhealthy');
                process.exit(1);
            }
        });

        req.on('error', () => {
            console.log('❌ Hermes API unreachable');
            process.exit(1);
        });

        req.setTimeout(5000, () => {
            console.log('❌ Health check timeout');
            process.exit(1);
        });

    } catch (error) {
        console.log('❌ RPC connectivity failed');
        process.exit(1);
    }
}

healthCheck();
EOF

# Environment variables with defaults
ENV NODE_ENV=production \
    LOG_LEVEL=info \
    HEALTH_CHECK_PORT=3000 \
    KEEPER_UPDATE_INTERVAL=5000 \
    MAX_GAS_PRICE=100000000000 \
    MIN_BALANCE_THRESHOLD=1.0

# Security: Run as non-root user
USER oracle

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD node /app/healthcheck.js

# Use tini for proper signal handling
ENTRYPOINT ["/sbin/tini", "--"]

# Graceful shutdown handling
CMD ["node", "keeper-polling.js"]

# Labels for production tracking
LABEL maintainer="protocol-team" \
      version="1.0.0" \
      description="Battle-tested Pyth Oracle Keeper for high-TVL protocols" \
      org.opencontainers.image.source="https://github.com/your-org/oracle-keeper"