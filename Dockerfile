# Multi-stage build for production optimization
FROM node:20-alpine AS builder

# Set working directory
WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci --only=production && npm cache clean --force

# Production stage
FROM node:20-alpine AS production

# Install dumb-init for proper signal handling
RUN apk add --no-cache dumb-init curl

# Create non-root user
RUN addgroup -g 1001 -S keeper && \
    adduser -S keeper -u 1001

# Set working directory
WORKDIR /app

# Copy dependencies from builder stage
COPY --from=builder /app/node_modules ./node_modules

# Copy application code
COPY --chown=keeper:keeper production-keeper-sse.js ./
COPY --chown=keeper:keeper package.json ./

# Create logs directory
RUN mkdir -p logs && chown -R keeper:keeper logs

# Create health check script
RUN cat > healthcheck.js << 'EOF'
const http = require('http');
const options = {
    hostname: 'localhost',
    port: 9090,
    path: '/health',
    method: 'GET',
    timeout: 5000
};

const req = http.request(options, (res) => {
    if (res.statusCode === 200) {
        console.log('✅ Health check passed');
        process.exit(0);
    } else {
        console.log('❌ Health check failed');
        process.exit(1);
    }
});

req.on('error', () => {
    console.log('❌ Health check error');
    process.exit(1);
});

req.on('timeout', () => {
    console.log('❌ Health check timeout');
    process.exit(1);
});

req.end();
EOF

# Environment variables with defaults
ENV NODE_ENV=production \
    LOG_LEVEL=info \
    METRICS_PORT=9090 \
    DEBOUNCE_MS=1000 \
    MAX_STALENESS=30 \
    RETRY_ATTEMPTS=3 \
    MIN_PRICE_CHANGE_PERCENT=0.01 \
    FORCE_UPDATE_INTERVAL_MS=300000

# Switch to non-root user
USER keeper

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD node healthcheck.js

# Expose metrics port
EXPOSE 9090

# Use dumb-init to handle signals properly
ENTRYPOINT ["dumb-init", "--"]

# Start the application
CMD ["node", "production-keeper-sse.js"]

# Labels for production tracking
LABEL maintainer="pyth-oracle-team" \
      version="2.0.0" \
      description="Production SSE-based Pyth Oracle Keeper with 99.99% uptime" \
      org.opencontainers.image.source="https://github.com/pyth-network/oracle-keeper"