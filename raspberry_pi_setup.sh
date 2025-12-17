#!/bin/bash
# Burnout Scoring System - Raspberry Pi Setup Script
# Run this on your Raspberry Pi after copying the project files

set -e

echo "========================================="
echo "Burnout Scoring - Raspberry Pi Setup"
echo "========================================="

# Update system
echo "Updating system..."
sudo apt update && sudo apt upgrade -y

# Install MongoDB
echo "Installing MongoDB..."
wget -qO - https://www.mongodb.org/static/pgp/server-7.0.asc | sudo apt-key add -
echo "deb [ arch=arm64 ] https://repo.mongodb.org/apt/ubuntu focal/mongodb-org/7.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-7.0.list
sudo apt update
sudo apt install -y mongodb-org
sudo systemctl start mongod
sudo systemctl enable mongod

# Install Python & dependencies
echo "Installing Python dependencies..."
sudo apt install -y python3-pip python3-venv
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
deactivate

# Install Node.js & Yarn
echo "Installing Node.js..."
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs
npm install -g yarn

# Configure backend environment
echo "Configuring backend..."
cd backend
cat > .env << EOF
MONGO_URL=mongodb://localhost:27017
DB_NAME=burnout_competition
JWT_SECRET=$(openssl rand -hex 32)
CORS_ORIGINS=*
EOF

# Build frontend
echo "Building frontend..."
cd ../frontend
PI_IP=$(hostname -I | awk '{print $1}')
cat > .env << EOF
REACT_APP_BACKEND_URL=http://${PI_IP}:8001
EOF
yarn install
yarn build

# Install and configure nginx
echo "Installing nginx..."
sudo apt install -y nginx

# Configure nginx to serve frontend and proxy backend
sudo cat > /etc/nginx/sites-available/burnout << EOF
server {
    listen 80;
    server_name _;

    # Frontend
    location / {
        root /home/pi/burnout-scoring/frontend/build;
        try_files \$uri /index.html;
    }

    # Backend API
    location /api {
        proxy_pass http://localhost:8001;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
    }
}
EOF

sudo ln -sf /etc/nginx/sites-available/burnout /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo systemctl restart nginx

# Create systemd service for backend
echo "Creating backend service..."
sudo cat > /etc/systemd/system/burnout-backend.service << EOF
[Unit]
Description=Burnout Scoring Backend
After=network.target mongod.service

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/burnout-scoring/backend
Environment="PATH=/home/pi/burnout-scoring/backend/venv/bin"
ExecStart=/home/pi/burnout-scoring/backend/venv/bin/uvicorn server:app --host 0.0.0.0 --port 8001
Restart=always

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable burnout-backend
sudo systemctl start burnout-backend

echo "========================================="
echo "Setup Complete!"
echo "========================================="
echo ""
echo "Access your scoring system at:"
echo "  http://${PI_IP}"
echo "  or http://$(hostname).local"
echo ""
echo "Default admin login:"
echo "  Username: admin"
echo "  Password: admin123"
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
