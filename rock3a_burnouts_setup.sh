#!/bin/bash
# Burnout Scoring System - Rock 3A Setup
# Customized for username: burnouts

set -e

PROJECT_USER="burnouts"
PROJECT_PATH="/home/${PROJECT_USER}/burnout-scoring"

echo "========================================="
echo "🔥 Burnout Scoring Setup for user: $PROJECT_USER"
echo "========================================="

# Verify we're running as the right user
CURRENT_USER=$(whoami)
if [ "$CURRENT_USER" != "$PROJECT_USER" ]; then
    echo "⚠️  Please run this script as user: $PROJECT_USER"
    echo "Current user: $CURRENT_USER"
    exit 1
fi

# Verify project directory exists
if [ ! -d "$PROJECT_PATH" ]; then
    echo "⚠️  Project directory not found: $PROJECT_PATH"
    echo "Please ensure your code is located at: $PROJECT_PATH"
    exit 1
fi

echo "✓ Running as: $CURRENT_USER"
echo "✓ Project path: $PROJECT_PATH"
echo ""

# System info
ARCH=$(uname -m)
TOTAL_RAM=$(free -m | awk '/^Mem:/{print $2}')
echo "Architecture: $ARCH"
echo "Total RAM: ${TOTAL_RAM}MB"
echo ""

# Update system
echo "📦 Updating system..."
sudo apt update && sudo apt upgrade -y

# Install dependencies
echo "📦 Installing dependencies..."
sudo apt install -y curl wget git build-essential
sudo apt install -y python3-pip python3-venv python3-dev
sudo apt install -y gcc g++ make libssl-dev libffi-dev
sudo apt install -y nginx

# Install MongoDB
echo "🍃 Installing MongoDB..."
if [ "$ARCH" = "aarch64" ]; then
    wget -qO - https://www.mongodb.org/static/pgp/server-7.0.asc | sudo apt-key add -
    echo "deb [ arch=arm64 ] https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/7.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-7.0.list
    sudo apt update
    sudo apt install -y mongodb-org
else
    sudo apt install -y mongodb
fi

sudo systemctl start mongod
sudo systemctl enable mongod
echo "✓ MongoDB started"

# Backend setup
echo ""
echo "🐍 Setting up Python backend..."
cd "$PROJECT_PATH/backend"

python3 -m venv venv
source venv/bin/activate

# Fixed requirements
cat > requirements.txt << 'EOF'
fastapi==0.110.1
uvicorn==0.25.0
python-dotenv
pymongo==4.5.0
motor==3.3.1
pydantic
passlib
bcrypt
pyjwt
python-jose[cryptography]
python-multipart
EOF

pip install --upgrade pip
pip install -r requirements.txt
deactivate

# Backend .env
cat > .env << EOF
MONGO_URL=mongodb://localhost:27017
DB_NAME=burnout_competition
JWT_SECRET=$(openssl rand -hex 32)
CORS_ORIGINS=*
EOF

echo "✓ Backend configured"

# Install Node.js
echo ""
echo "📗 Installing Node.js..."
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs
sudo npm install -g yarn
echo "✓ Node.js installed"

# Frontend setup
echo ""
echo "⚛️  Building frontend..."
cd "$PROJECT_PATH/frontend"

BOARD_IP=$(hostname -I | awk '{print $1}')
cat > .env << EOF
REACT_APP_BACKEND_URL=http://${BOARD_IP}:8001
EOF

# Set Node memory based on RAM
if [ "$TOTAL_RAM" -ge 4096 ]; then
    export NODE_OPTIONS="--max-old-space-size=2048"
else
    export NODE_OPTIONS="--max-old-space-size=1536"
fi

yarn install
yarn build

if [ ! -d "build" ]; then
    echo "✗ Frontend build failed!"
    exit 1
fi

echo "✓ Frontend built"

# Configure Nginx
echo ""
echo "🌐 Configuring nginx..."
sudo cat > /etc/nginx/sites-available/burnout << EOF
server {
    listen 80 default_server;
    server_name _;

    location / {
        root $PROJECT_PATH/frontend/build;
        try_files \$uri /index.html;
        
        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2)$ {
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
    }

    location /api {
        proxy_pass http://localhost:8001;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_read_timeout 180s;
    }
}
EOF

sudo rm -f /etc/nginx/sites-enabled/default
sudo ln -sf /etc/nginx/sites-available/burnout /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
echo "✓ Nginx configured"

# Create systemd service
echo ""
echo "🔧 Creating backend service..."

WORKERS=2
if [ "$TOTAL_RAM" -ge 4096 ]; then
    WORKERS=3
fi

sudo cat > /etc/systemd/system/burnout-backend.service << EOF
[Unit]
Description=Burnout Scoring Backend
After=network.target mongod.service

[Service]
Type=simple
User=$PROJECT_USER
WorkingDirectory=$PROJECT_PATH/backend
Environment="PATH=$PROJECT_PATH/backend/venv/bin"
ExecStart=$PROJECT_PATH/backend/venv/bin/uvicorn server:app --host 0.0.0.0 --port 8001 --workers $WORKERS
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable burnout-backend
sudo systemctl start burnout-backend
echo "✓ Backend service started"

# Wait and check status
sleep 3

MONGO_STATUS=$(sudo systemctl is-active mongod)
BACKEND_STATUS=$(sudo systemctl is-active burnout-backend)
NGINX_STATUS=$(sudo systemctl is-active nginx)

echo ""
echo "========================================="
echo "✅ Setup Complete!"
echo "========================================="
echo ""
echo "🔥 BURNOUT SCORING SYSTEM READY"
echo ""
echo "🌐 Access at: http://${BOARD_IP}"
echo ""
echo "👤 Default Login:"
echo "   Username: admin"
echo "   Password: admin123"
echo ""
echo "📊 Service Status:"
echo "   MongoDB: $MONGO_STATUS"
echo "   Backend: $BACKEND_STATUS"
echo "   Nginx: $NGINX_STATUS"
echo ""
echo "🔧 Useful Commands:"
echo "   sudo systemctl status burnout-backend"
echo "   sudo systemctl restart burnout-backend"
echo "   sudo journalctl -u burnout-backend -f"
echo ""
echo "Ready for competition! 🏁"
echo "========================================="
