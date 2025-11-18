#!/bin/bash
# Quick update script for JalebiJams Discord Bot
# Run this on your VPS when you've pushed updates to git

set -e

echo "🔄 Updating JalebiJams..."

# Pull latest changes
git pull

# Activate venv and update dependencies if requirements changed
source venv/bin/activate
pip install -r requirements.txt --upgrade

# Restart the bot service
sudo systemctl restart jalebi-bot

echo "✅ Bot updated and restarted!"
echo ""
echo "Check status: sudo systemctl status jalebi-bot"
echo "View logs:    sudo journalctl -u jalebi-bot -f"
