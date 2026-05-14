#!/usr/bin/env bash
set -e

echo "========================================"
echo "  Titan Manager Bot - Railway Deploy"
echo "========================================"

cd "$(dirname "$0")"

echo "[1/4] Installing Python dependencies..."
pip3 install -r requirements.txt -q

echo "[2/4] Cleaning old data..."
rm -rf data/

echo "[3/4] Bot is ready!"
echo ""
echo "To start the bot:"
echo "  screen -S titan"
echo "  python3 bot.py"
echo "  (Ctrl+A then D to detach)"
echo ""
echo "To keep it running permanently:"
echo "  nano /etc/systemd/system/titanbot.service"
echo "  (paste the service file below)"
echo ""

cat << 'SERVICE'
[Unit]
Description=Titan Manager Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/bot
ExecStart=/usr/bin/python3 /root/bot/bot.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
SERVICE

echo ""
echo "Then run:"
echo "  systemctl daemon-reload"
echo "  systemctl enable --now titanbot"
echo "  systemctl status titanbot"
echo ""
echo "========================================"
echo "  Bot URL for OAuth2:"
echo "  Update this in config.py if needed:"
echo "  OAUTH2_REDIRECT_URI"
echo "========================================"
