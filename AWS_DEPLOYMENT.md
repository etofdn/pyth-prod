# 🚀 AWS Deployment Guide - MAANG Oracle

## **📋 Quick Setup (5 minutes)**

### **1. Launch EC2 Instance**
```bash
# Launch t3.medium Ubuntu 22.04 LTS
# Security Group: SSH (22), HTTP (80), HTTPS (443), Custom (3000)
# Key Pair: Your existing key
```

### **2. Connect & Deploy**
```bash
# SSH into your instance
ssh -i your-key.pem ubuntu@your-ec2-ip

# Clone the repository
git clone https://github.com/your-repo/pyth-prod.git
cd pyth-prod

# Make deploy script executable
chmod +x aws/deploy.sh

# Edit the script with your credentials
nano aws/deploy.sh
# Replace YOUR_PRIVATE_KEY_HERE and YOUR_RPC_URL_HERE

# Run deployment
./aws/deploy.sh
```

### **3. Setup Dashboard**
```bash
# Navigate to dashboard
cd dashboard

# Install dependencies
npm install

# Start dashboard
npm start

# Setup PM2 for dashboard too
pm2 start server.js --name "maang-dashboard" --watch
pm2 save
```

### **4. Setup Nginx (Optional)**
```bash
# Install nginx
sudo apt install nginx -y

# Create nginx config
sudo tee /etc/nginx/sites-available/maang-oracle > /dev/null <<EOF
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_cache_bypass \$http_upgrade;
    }
}
EOF

# Enable site
sudo ln -s /etc/nginx/sites-available/maang-oracle /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

## **📊 Monitoring & Management**

### **Check Keeper Status**
```bash
# Check systemd service
sudo systemctl status maang-keeper

# View keeper logs
sudo journalctl -u maang-keeper -f

# Check PM2 processes
pm2 status
pm2 logs maang-keeper
```

### **Check Dashboard**
```bash
# Check dashboard
pm2 logs maang-dashboard

# Restart services
pm2 restart maang-keeper
pm2 restart maang-dashboard
```

### **Access Dashboard**
- **Direct**: `http://your-ec2-ip:3000`
- **Via Domain**: `http://your-domain.com` (if nginx setup)

## **🔧 Environment Variables**

Create `.env` file:
```bash
# .env
PRIVATE_KEY=your_private_key_here
RPC_URL=your_rpc_url_here
NODE_ENV=production
PORT=3000
```

## **📈 What You Get**

### **Keeper Service**
- ✅ Runs automatically on boot
- ✅ Restarts on failure
- ✅ Updates MAANG oracle every 30 seconds
- ✅ Logs to systemd/journal

### **Dashboard**
- ✅ Real-time MAANG index price
- ✅ Individual stock prices (META, AAPL, AMZN, NVDA, GOOGL)
- ✅ Status indicators (Live/Stale)
- ✅ Auto-refresh every 30 seconds
- ✅ Beautiful responsive UI

### **API Endpoints**
- `GET /api/status` - Oracle status
- `GET /health` - Health check

## **💰 Cost Estimate**
- **EC2 t3.medium**: ~$30/month
- **Data transfer**: ~$5/month
- **Total**: ~$35/month

## **🛡️ Security Notes**
- Use environment variables for secrets
- Setup proper security groups
- Consider using AWS Secrets Manager for production
- Enable CloudWatch logging for audit trails

## **📞 Support**
If anything breaks:
1. Check logs: `pm2 logs`
2. Restart services: `pm2 restart all`
3. Check system status: `sudo systemctl status maang-keeper`
