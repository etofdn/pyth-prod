#!/bin/bash

# AWS EC2 Deployment Script for MAANG Oracle Keeper
echo "🚀 Deploying MAANG Oracle Keeper to EC2..."

# Update system
sudo apt update && sudo apt upgrade -y

# Install Node.js 18
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs

# Install PM2 for process management
sudo npm install -g pm2

# Install dependencies
npm install

# Create systemd service for auto-start
sudo tee /etc/systemd/system/maang-keeper.service > /dev/null <<EOF
[Unit]
Description=MAANG Oracle Keeper
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/pyth-prod
ExecStart=/usr/bin/node keeper-polling.js
Restart=always
RestartSec=10
Environment=NODE_ENV=production
Environment=PRIVATE_KEY=YOUR_PRIVATE_KEY_HERE
Environment=RPC_URL=YOUR_RPC_URL_HERE

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable maang-keeper
sudo systemctl start maang-keeper

# Setup PM2 for better process management
pm2 start keeper-polling.js --name "maang-keeper" --watch
pm2 startup
pm2 save

echo "✅ MAANG Keeper deployed and running!"
echo "📊 Check status: sudo systemctl status maang-keeper"
echo "📝 View logs: sudo journalctl -u maang-keeper -f"
