#!/usr/bin/env bash
# Step 2: makes the bot start automatically, restart if it crashes, and survive reboots.  Run:  bash install_service.sh
set -e
cd "$(dirname "$0")"
DIR="$(pwd)"
sudo tee /etc/systemd/system/posterbot.service >/dev/null <<UNIT
[Unit]
Description=Manhwa poster Telegram bot
After=network-online.target
Wants=network-online.target

[Service]
User=$USER
WorkingDirectory=$DIR
ExecStart=$DIR/venv/bin/python run.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
UNIT
sudo systemctl daemon-reload
sudo systemctl enable --now posterbot
echo
echo "Bot is running. Useful commands:"
echo "  sudo systemctl status posterbot      # is it running?"
echo "  sudo journalctl -u posterbot -f      # live logs (Ctrl+C to leave)"
echo "  sudo systemctl restart posterbot     # restart after you change a file"
