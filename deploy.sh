#!/bin/bash
# Deploy script for JalebiJams Discord Bot
# Run this script on your VPS after cloning the repo

set -e  # Exit on error

echo "🎵 JalebiJams Deployment Script"
echo "================================"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get the current username
USERNAME=$(whoami)
INSTALL_DIR="$HOME/JalebiJams"

echo -e "${YELLOW}Installing system dependencies...${NC}"
sudo apt update
sudo apt install -y python3 python3-pip python3-venv git ffmpeg

echo -e "${YELLOW}Setting up Python virtual environment...${NC}"
cd "$INSTALL_DIR"
python3 -m venv venv
source venv/bin/activate

echo -e "${YELLOW}Installing Python packages...${NC}"
pip install --upgrade pip
pip install -r requirements.txt

echo -e "${YELLOW}Setting up .env file...${NC}"
if [ ! -f .env ]; then
    cp .env.example .env
    echo -e "${YELLOW}Please edit .env and add your Discord token:${NC}"
    echo "nano .env"
    read -p "Press Enter after you've added your token..."
fi

echo -e "${YELLOW}Setting up systemd service...${NC}"
# Create service file with correct username
sed "s/REPLACE_WITH_YOUR_USERNAME/$USERNAME/g" jalebi-bot.service > /tmp/jalebi-bot.service
sudo cp /tmp/jalebi-bot.service /etc/systemd/system/jalebi-bot.service
sudo systemctl daemon-reload

echo -e "${YELLOW}Enabling and starting the bot service...${NC}"
sudo systemctl enable jalebi-bot
sudo systemctl start jalebi-bot

echo -e "${GREEN}✅ Deployment complete!${NC}"
echo ""
echo "Useful commands:"
echo "  Check status:    sudo systemctl status jalebi-bot"
echo "  View logs:       sudo journalctl -u jalebi-bot -f"
echo "  Restart bot:     sudo systemctl restart jalebi-bot"
echo "  Stop bot:        sudo systemctl stop jalebi-bot"
echo ""
echo "Check if the bot is running:"
sudo systemctl status jalebi-bot
