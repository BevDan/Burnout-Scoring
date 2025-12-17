#!/bin/bash
# Burnout Scoring System - Radxa Rock 3C Setup Script
# Run this on your Radxa Rock 3C after copying the project files

set -e

echo "========================================="
echo "Burnout Scoring - Radxa Rock 3C Setup"
echo "========================================="

# Detect architecture
ARCH=$(uname -m)
echo "Detected architecture: $ARCH"

# Update system
echo "Updating system..."
sudo apt update && sudo apt upgrade -y

# Install MongoDB (ARM64 optimized)
echo "Installing MongoDB..."
if [ "$ARCH" = "aarch64" ]; then
    wget -qO - https://www.mongodb.org/static/pgp/server-7.0.asc | sudo apt-key add -
    echo "deb [ arch=arm64 ] https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/7.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-7.0.list
    sudo apt update
    sudo apt install -y mongodb-org
else
    # For 32-bit ARM, use alternative
    sudo apt install -y mongodb
fi

sudo systemctl start mongod
sudo systemctl enable mongod

# Optimize MongoDB for Rock 3C
echo "Optimizing MongoDB configuration..."
sudo mkdir -p /etc/systemd/system/mongod.service.d/
sudo cat > /etc/systemd/system/mongod.service.d/override.conf << EOF
[Service]
# Limit memory usage for smaller SBC
Environment="MALLOC_ARENA_MAX=2"
LimitNOFILE=64000
EOF

sudo systemctl daemon-reload
sudo systemctl restart mongod

# Install Python & dependencies
echo "Installing Python dependencies..."
sudo apt install -y python3-pip python3-venv python3-dev gcc
cd /home/radxa/burnout-scoring/backend || cd /home/rock/burnout-scoring/backend
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
deactivate

# Install Node.js 18 (optimized for ARM)
echo "Installing Node.js..."
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs
npm install -g yarn

# Configure backend environment
echo "Configuring backend..."
cat > .env << EOF
MONGO_URL=mongodb://localhost:27017
DB_NAME=burnout_competition
JWT_SECRET=$(openssl rand -hex 32)
CORS_ORIGINS=*
EOF

# Build frontend
echo "Building frontend..."
cd ../frontend
BOARD_IP=$(hostname -I | awk '{print $1}')
cat > .env << EOF
REACT_APP_BACKEND_URL=http://${BOARD_IP}:8001
EOF

# Increase Node memory limit for Rock 3C (if 2GB+ RAM)
export NODE_OPTIONS="--max-old-space-size=1536"
yarn install
yarn build

# Install and configure nginx
echo "Installing nginx..."
sudo apt install -y nginx

# Detect user (radxa or rock)
CURRENT_USER=$(whoami)
PROJECT_PATH="/home/${CURRENT_USER}/burnout-scoring"

# Configure nginx
sudo cat > /etc/nginx/sites-available/burnout << EOF
server {
    listen 80;
    server_name _;

    # Optimize for SBC
    client_max_body_size 10M;
    client_body_timeout 30s;
    
    # Frontend
    location / {
        root ${PROJECT_PATH}/frontend/build;
        try_files \$uri /index.html;
        
        # Cache static assets
        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2)$ {
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
    }

    # Backend API
    location /api {
        proxy_pass http://localhost:8001;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        
        # Increase timeout for CSV imports
        proxy_read_timeout 120s;
        proxy_connect_timeout 30s;
    }
}
EOF

sudo ln -sf /etc/nginx/sites-available/burnout /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl restart nginx

# Create systemd service for backend
echo "Creating backend service..."
sudo cat > /etc/systemd/system/burnout-backend.service << EOF
[Unit]
Description=Burnout Scoring Backend
After=network.target mongod.service

[Service]
Type=simple
User=${CURRENT_USER}
WorkingDirectory=${PROJECT_PATH}/backend
Environment="PATH=${PROJECT_PATH}/backend/venv/bin"
ExecStart=${PROJECT_PATH}/backend/venv/bin/uvicorn server:app --host 0.0.0.0 --port 8001 --workers 2
Restart=always
RestartSec=10

# Resource limits for Rock 3C
MemoryMax=512M
CPUQuota=150%

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable burnout-backend
sudo systemctl start burnout-backend

# Performance tuning for Rock 3C
echo "Applying performance optimizations..."
# Increase swap if less than 4GB RAM
TOTAL_RAM=$(free -m | awk '/^Mem:/{print $2}')
if [ "$TOTAL_RAM" -lt 4096 ]; then
    echo "Adding swap space for better performance..."
    sudo fallocate -l 2G /swapfile
    sudo chmod 600 /swapfile
    sudo mkswap /swapfile
    sudo swapon /swapfile
    echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
fi

# Set CPU governor to performance during scoring
echo 'GOVERNOR="performance"' | sudo tee /etc/default/cpufrequtils
sudo systemctl restart cpufrequtils || true

echo "========================================="
echo "Setup Complete!"
echo "========================================="
echo ""
echo "🔥 Burnout Scoring System Ready!"
echo ""
echo "Access your scoring system at:"
echo "  http://${BOARD_IP}"
echo "  or http://$(hostname).local"
echo ""
echo "Default admin login:"
echo "  Username: admin"
echo "  Password: admin123"
echo ""
echo "Hardware detected:"
echo "  Board: Radxa Rock 3C"
echo "  RAM: ${TOTAL_RAM}MB"
echo "  Architecture: ${ARCH}"
echo ""
echo "Services running:"
echo "  - MongoDB: localhost:27017"
echo "  - Backend API: localhost:8001"
echo "  - Frontend: port 80 (nginx)"
echo ""
echo "To check status:"
echo "  sudo systemctl status burnout-backend"
echo "  sudo systemctl status mongod"
echo "  sudo systemctl status nginx"
echo ""
echo "Performance tips:"
echo "  - Use ethernet for best stability"
echo "  - 2GB+ RAM recommended for multiple judges"
echo "  - Consider NVMe addon for faster database"
echo ""
