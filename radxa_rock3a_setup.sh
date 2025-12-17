#!/bin/bash
# Burnout Scoring System - Radxa Rock 3A Setup Script
# Optimized for Rock 3A (2GB/4GB/8GB versions)

set -e

echo "========================================="
echo "🔥 Burnout Scoring - Radxa Rock 3A Setup"
echo "========================================="

# Detect system info
ARCH=$(uname -m)
TOTAL_RAM=$(free -m | awk '/^Mem:/{print $2}')
echo "Architecture: $ARCH"
echo "Total RAM: ${TOTAL_RAM}MB"

# Update system
echo ""
echo "📦 Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install system dependencies
echo ""
echo "📦 Installing system dependencies..."
sudo apt install -y curl wget git build-essential python3-pip python3-venv python3-dev gcc nginx

# Install MongoDB (ARM64 optimized for Rock 3A)
echo ""
echo "🍃 Installing MongoDB..."
if [ "$ARCH" = "aarch64" ]; then
    # MongoDB 7.0 for ARM64
    wget -qO - https://www.mongodb.org/static/pgp/server-7.0.asc | sudo apt-key add -
    echo "deb [ arch=arm64 ] https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/7.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-7.0.list
    sudo apt update
    sudo apt install -y mongodb-org
else
    echo "⚠️  32-bit ARM detected. Using alternative MongoDB..."
    sudo apt install -y mongodb
fi

# Start and enable MongoDB
sudo systemctl start mongod
sudo systemctl enable mongod

# Optimize MongoDB for Rock 3A (works great with 2GB+)
echo ""
echo "⚙️  Optimizing MongoDB for Rock 3A..."
sudo mkdir -p /etc/systemd/system/mongod.service.d/
sudo cat > /etc/systemd/system/mongod.service.d/override.conf << EOF
[Service]
# Rock 3A optimizations
Environment="MALLOC_ARENA_MAX=2"
LimitNOFILE=64000

# Cache size based on RAM
$(if [ "$TOTAL_RAM" -ge 4096 ]; then
    echo 'Environment="MONGO_CACHE_SIZE_GB=1"'
else
    echo 'Environment="MONGO_CACHE_SIZE_GB=0.5"'
fi)
EOF

sudo systemctl daemon-reload
sudo systemctl restart mongod

# Wait for MongoDB to be ready
echo "Waiting for MongoDB to start..."
sleep 5
until sudo systemctl is-active --quiet mongod; do
    echo "  Waiting for MongoDB..."
    sleep 2
done
echo "✓ MongoDB is running"

# Detect project directory
CURRENT_USER=$(whoami)
if [ -d "/home/radxa/burnout-scoring" ]; then
    PROJECT_PATH="/home/radxa/burnout-scoring"
elif [ -d "/home/rock/burnout-scoring" ]; then
    PROJECT_PATH="/home/rock/burnout-scoring"
else
    echo "⚠️  Project directory not found. Please ensure code is at /home/${CURRENT_USER}/burnout-scoring"
    exit 1
fi

echo ""
echo "📁 Project location: $PROJECT_PATH"

# Install Python dependencies
echo ""
echo "🐍 Setting up Python backend..."
cd "$PROJECT_PATH/backend"
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
deactivate
echo "✓ Python dependencies installed"

# Install Node.js 18 LTS
echo ""
echo "📗 Installing Node.js 18 LTS..."
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs
npm install -g yarn
echo "✓ Node.js $(node --version) installed"

# Configure backend environment
echo ""
echo "⚙️  Configuring backend..."
cd "$PROJECT_PATH/backend"
cat > .env << EOF
MONGO_URL=mongodb://localhost:27017
DB_NAME=burnout_competition
JWT_SECRET=$(openssl rand -hex 32)
CORS_ORIGINS=*
EOF
echo "✓ Backend configured"

# Build frontend
echo ""
echo "⚛️  Building React frontend..."
cd "$PROJECT_PATH/frontend"

# Get Rock 3A IP address
BOARD_IP=$(hostname -I | awk '{print $1}')
cat > .env << EOF
REACT_APP_BACKEND_URL=http://${BOARD_IP}:8001
WDS_SOCKET_PORT=443
REACT_APP_ENABLE_VISUAL_EDITS=false
ENABLE_HEALTH_CHECK=false
EOF

# Set Node memory limit based on available RAM
if [ "$TOTAL_RAM" -ge 8192 ]; then
    export NODE_OPTIONS="--max-old-space-size=3072"
elif [ "$TOTAL_RAM" -ge 4096 ]; then
    export NODE_OPTIONS="--max-old-space-size=2048"
else
    export NODE_OPTIONS="--max-old-space-size=1536"
fi

echo "Building with memory limit: $NODE_OPTIONS"
yarn install
yarn build
echo "✓ Frontend built successfully"

# Configure nginx
echo ""
echo "🌐 Configuring nginx web server..."
sudo cat > /etc/nginx/sites-available/burnout << EOF
# Burnout Scoring - Nginx Configuration for Rock 3A
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name _;

    # Optimize for Rock 3A
    client_max_body_size 20M;
    client_body_timeout 60s;
    keepalive_timeout 65;
    
    # Frontend - React SPA
    location / {
        root $PROJECT_PATH/frontend/build;
        try_files \$uri /index.html;
        
        # Cache static assets aggressively
        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
        
        # Don't cache index.html
        location = /index.html {
            add_header Cache-Control "no-cache, no-store, must-revalidate";
        }
    }

    # Backend API proxy
    location /api {
        proxy_pass http://localhost:8001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # Longer timeout for CSV imports and large operations
        proxy_read_timeout 180s;
        proxy_connect_timeout 60s;
        proxy_send_timeout 180s;
    }
}
EOF

# Enable site
sudo ln -sf /etc/nginx/sites-available/burnout /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Test and reload nginx
sudo nginx -t && sudo systemctl restart nginx
echo "✓ Nginx configured"

# Create systemd service for backend
echo ""
echo "🔧 Creating backend systemd service..."

# Determine workers based on RAM
if [ "$TOTAL_RAM" -ge 8192 ]; then
    WORKERS=4
elif [ "$TOTAL_RAM" -ge 4096 ]; then
    WORKERS=3
else
    WORKERS=2
fi

sudo cat > /etc/systemd/system/burnout-backend.service << EOF
[Unit]
Description=Burnout Scoring Backend API
Documentation=https://github.com/yourusername/burnout-scoring
After=network.target mongod.service
Wants=mongod.service

[Service]
Type=simple
User=$CURRENT_USER
WorkingDirectory=$PROJECT_PATH/backend
Environment="PATH=$PROJECT_PATH/backend/venv/bin"
ExecStart=$PROJECT_PATH/backend/venv/bin/uvicorn server:app --host 0.0.0.0 --port 8001 --workers $WORKERS
Restart=always
RestartSec=10

# Resource limits optimized for Rock 3A
$(if [ "$TOTAL_RAM" -ge 4096 ]; then
    echo "MemoryMax=1G"
else
    echo "MemoryMax=768M"
fi)
CPUQuota=200%

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=burnout-backend

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable burnout-backend
sudo systemctl start burnout-backend
echo "✓ Backend service started with $WORKERS workers"

# Performance tuning for Rock 3A
echo ""
echo "⚡ Applying Rock 3A performance optimizations..."

# Add swap if needed (2GB for systems with 2GB RAM, 1GB for 4GB+)
if [ ! -f /swapfile ]; then
    if [ "$TOTAL_RAM" -lt 4096 ]; then
        SWAP_SIZE="2G"
    else
        SWAP_SIZE="1G"
    fi
    
    echo "Creating ${SWAP_SIZE} swap file..."
    sudo fallocate -l $SWAP_SIZE /swapfile
    sudo chmod 600 /swapfile
    sudo mkswap /swapfile
    sudo swapon /swapfile
    echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
    echo "✓ Swap configured"
fi

# Set CPU governor to performance
echo "Setting CPU to performance mode..."
echo 'GOVERNOR="performance"' | sudo tee /etc/default/cpufrequtils
sudo apt install -y cpufrequtils
sudo systemctl restart cpufrequtils 2>/dev/null || true

# I/O scheduler optimization for Rock 3A
echo "Optimizing I/O scheduler..."
echo 'ACTION=="add|change", KERNEL=="mmcblk[0-9]", ATTR{queue/scheduler}="deadline"' | sudo tee /etc/udev/rules.d/60-ioschedulers.rules

# Wait for services to stabilize
echo ""
echo "⏳ Waiting for services to stabilize..."
sleep 5

# Check service status
echo ""
echo "🔍 Checking service status..."
MONGO_STATUS=$(sudo systemctl is-active mongod)
BACKEND_STATUS=$(sudo systemctl is-active burnout-backend)
NGINX_STATUS=$(sudo systemctl is-active nginx)

echo "  MongoDB: $MONGO_STATUS"
echo "  Backend: $BACKEND_STATUS"
echo "  Nginx: $NGINX_STATUS"

# Final system info
echo ""
echo "========================================="
echo "✅ Setup Complete!"
echo "========================================="
echo ""
echo "🔥 BURNOUT SCORING SYSTEM READY"
echo ""
echo "🌐 Access URLs:"
echo "  ➜ http://${BOARD_IP}"
echo "  ➜ http://$(hostname).local (if mDNS configured)"
echo ""
echo "👤 Default Admin Login:"
echo "  Username: admin"
echo "  Password: admin123"
echo "  ⚠️  CHANGE THIS PASSWORD IMMEDIATELY!"
echo ""
echo "💻 System Information:"
echo "  Board: Radxa Rock 3A"
echo "  RAM: ${TOTAL_RAM}MB"
echo "  CPU: RK3568 (Cortex-A55 quad-core)"
echo "  Architecture: ${ARCH}"
echo "  Backend Workers: $WORKERS"
echo ""
echo "📊 Services:"
echo "  MongoDB: localhost:27017 ($MONGO_STATUS)"
echo "  Backend API: localhost:8001 ($BACKEND_STATUS)"
echo "  Frontend: port 80 via nginx ($NGINX_STATUS)"
echo ""
echo "🔧 Useful Commands:"
echo "  sudo systemctl status burnout-backend  # Check backend status"
echo "  sudo systemctl restart burnout-backend # Restart backend"
echo "  sudo journalctl -u burnout-backend -f  # View live logs"
echo "  mongodump --out=/home/$CURRENT_USER/backup  # Backup database"
echo ""
echo "💡 Rock 3A Specific Tips:"
echo "  - Use Gigabit Ethernet for best performance"
echo "  - Connect HDMI display for live leaderboard"
echo "  - ${TOTAL_RAM}MB RAM supports 10+ simultaneous judges"
echo "  - Add NVMe SSD via M.2 for faster database"
echo "  - USB ports available for WiFi dongles/peripherals"
echo ""
echo "📺 For Leaderboard Display:"
echo "  Open http://${BOARD_IP}/leaderboard on HDMI-connected display"
echo "  Set browser to fullscreen (F11)"
echo ""
echo "🎯 Ready for competition day!"
echo "========================================="
