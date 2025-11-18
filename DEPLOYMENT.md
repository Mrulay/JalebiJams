# Deploying JalebiJams to VPS

## Prerequisites

- A VPS running Ubuntu/Debian (or similar Linux distro)
- SSH access to your VPS
- Python 3.8+ on the VPS
- FFmpeg on the VPS

## Step 1: Prepare Your VPS

SSH into your VPS:
```bash
ssh username@your-vps-ip
```

Update system packages:
```bash
sudo apt update && sudo apt upgrade -y
```

Install required dependencies:
```bash
# Install Python, pip, git, and FFmpeg
sudo apt install -y python3 python3-pip python3-venv git ffmpeg

# Verify installations
python3 --version
ffmpeg -version
```

## Step 2: Push Code to VPS

### Option A: Using Git (Recommended)

**On your local machine:**

1. Initialize git if not already done:
```bash
cd /Users/mrulay/Desktop/Therapix/JalebiJams
git init
git add .
git commit -m "Initial commit with playlist support"
```

2. Push to GitHub:
```bash
# Create a new repo on GitHub, then:
git remote add origin https://github.com/Mrulay/JalebiJams.git
git branch -M main
git push -u origin main
```

**On your VPS:**

Clone the repository:
```bash
cd ~
git clone https://github.com/Mrulay/JalebiJams.git
cd JalebiJams
```

### Option B: Using SCP (Direct Transfer)

**On your local machine:**

```bash
# Transfer the entire directory (excluding venv)
cd /Users/mrulay/Desktop/Therapix
tar --exclude='JalebiJams/venv' -czf jalebi.tar.gz JalebiJams/
scp jalebi.tar.gz username@your-vps-ip:~/

# On VPS, extract:
# ssh username@your-vps-ip
# tar -xzf jalebi.tar.gz
# cd JalebiJams
```

## Step 3: Setup on VPS

**On your VPS:**

Create virtual environment:
```bash
cd ~/JalebiJams
python3 -m venv venv
source venv/bin/activate
```

Install dependencies:
```bash
pip install -r requirements.txt
```

Create and configure `.env` file:
```bash
cp .env.example .env
nano .env
```

Add your Discord bot token and save (Ctrl+X, Y, Enter).

## Step 4: Test the Bot

Run the bot manually first to ensure it works:
```bash
source venv/bin/activate
python bot.py
```

If you see "JalebiJams has connected to Discord!", it's working! Press Ctrl+C to stop.

## Step 5: Run Bot as a Background Service

Create a systemd service file:
```bash
sudo nano /etc/systemd/system/jalebi-bot.service
```

Paste this configuration (replace `username` with your actual username):
```ini
[Unit]
Description=JalebiJams Discord Music Bot
After=network.target

[Service]
Type=simple
User=username
WorkingDirectory=/home/username/JalebiJams
Environment="PATH=/home/username/JalebiJams/venv/bin"
ExecStart=/home/username/JalebiJams/venv/bin/python /home/username/JalebiJams/bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable jalebi-bot
sudo systemctl start jalebi-bot
```

Check status:
```bash
sudo systemctl status jalebi-bot
```

View logs:
```bash
sudo journalctl -u jalebi-bot -f
```

## Managing the Bot

**Start the bot:**
```bash
sudo systemctl start jalebi-bot
```

**Stop the bot:**
```bash
sudo systemctl stop jalebi-bot
```

**Restart the bot:**
```bash
sudo systemctl restart jalebi-bot
```

**View logs:**
```bash
sudo journalctl -u jalebi-bot -n 50  # Last 50 lines
sudo journalctl -u jalebi-bot -f     # Follow live
```

## Updating the Bot

When you make changes locally:

**Using Git:**
```bash
# On local machine
git add .
git commit -m "Update description"
git push

# On VPS
cd ~/JalebiJams
git pull
sudo systemctl restart jalebi-bot
```

**Using SCP:**
```bash
# On local machine
scp bot.py username@your-vps-ip:~/JalebiJams/

# On VPS
sudo systemctl restart jalebi-bot
```

## Troubleshooting

**Bot won't start:**
- Check logs: `sudo journalctl -u jalebi-bot -n 100`
- Verify `.env` file exists and has correct token
- Ensure FFmpeg is installed: `which ffmpeg`

**No audio in Discord:**
- Verify FFmpeg is installed
- Check bot has "Connect" and "Speak" permissions
- Restart the bot: `sudo systemctl restart jalebi-bot`

**After VPS reboot:**
The bot should auto-start. If not:
```bash
sudo systemctl enable jalebi-bot
sudo systemctl start jalebi-bot
```

## Security Notes

- Never commit `.env` file to git
- Keep your VPS updated: `sudo apt update && sudo apt upgrade`
- Use SSH keys instead of passwords for VPS access
- Consider using a firewall: `sudo ufw allow 22 && sudo ufw enable`
