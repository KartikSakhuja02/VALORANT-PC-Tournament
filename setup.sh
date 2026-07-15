#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
#  setup.sh — One-shot Raspberry Pi setup script for the VALORANT Tournament Bot
#
#  Run once on a fresh Pi (from /home/pi/Documents/ValorantPCTournament):
#    chmod +x setup.sh && ./setup.sh
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_NAME="valorant-bot"
SERVICE_FILE="$PROJECT_DIR/valorant-bot.service"
SYSTEMD_PATH="/etc/systemd/system/$SERVICE_NAME.service"

echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║   VALORANT PC Tournament Bot — Pi Setup Script   ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""

# ── 1. System dependencies ────────────────────────────────────────────────────
echo "▶ [1/5] Updating package list and installing python3-venv..."
sudo apt-get update -qq
sudo apt-get install -y -qq python3 python3-venv python3-pip git

# ── 2. Virtual environment ────────────────────────────────────────────────────
echo "▶ [2/5] Creating Python virtual environment..."
if [ ! -d "$PROJECT_DIR/venv" ]; then
    python3 -m venv "$PROJECT_DIR/venv"
    echo "   Created venv at $PROJECT_DIR/venv"
else
    echo "   venv already exists — skipping."
fi

# ── 3. Install Python dependencies ───────────────────────────────────────────
echo "▶ [3/5] Installing Python dependencies..."
"$PROJECT_DIR/venv/bin/pip" install --upgrade pip --quiet
"$PROJECT_DIR/venv/bin/pip" install -r "$PROJECT_DIR/requirements.txt" --quiet
echo "   Dependencies installed."

# ── 4. Create .env from template ─────────────────────────────────────────────
echo "▶ [4/5] Setting up .env configuration..."
if [ ! -f "$PROJECT_DIR/.env" ]; then
    cp "$PROJECT_DIR/.env.example" "$PROJECT_DIR/.env"
    echo ""
    echo "   ⚠️  .env file created from template."
    echo "   → Open it now and fill in your DISCORD_TOKEN and GUILD_ID:"
    echo "      nano $PROJECT_DIR/.env"
    echo ""
    read -rp "   Press ENTER once you've filled in .env to continue... " _
else
    echo "   .env already exists — skipping."
fi

# ── 5. Install & enable systemd services ─────────────────────────────────────
echo "▶ [5/5] Installing systemd services..."

CURRENT_USER="$(whoami)"

# Configure bot service
TMP_BOT_SERVICE=$(mktemp)
sed \
    -e "s|User=kartiksakhuja02|User=$CURRENT_USER|g" \
    -e "s|Group=kartiksakhuja02|Group=$CURRENT_USER|g" \
    -e "s|WorkingDirectory=.*|WorkingDirectory=$PROJECT_DIR|g" \
    -e "s|ExecStart=.*|ExecStart=$PROJECT_DIR/venv/bin/python bot.py|g" \
    -e "s|ReadWritePaths=.*|ReadWritePaths=$PROJECT_DIR|g" \
    "$SERVICE_FILE" > "$TMP_BOT_SERVICE"

sudo cp "$TMP_BOT_SERVICE" "$SYSTEMD_PATH"
rm "$TMP_BOT_SERVICE"

# Configure web service
WEB_SERVICE_FILE="$PROJECT_DIR/valorant-web.service"
WEB_SYSTEMD_PATH="/etc/systemd/system/valorant-web.service"
TMP_WEB_SERVICE=$(mktemp)
sed \
    -e "s|User=kartiksakhuja02|User=$CURRENT_USER|g" \
    -e "s|Group=kartiksakhuja02|Group=$CURRENT_USER|g" \
    -e "s|WorkingDirectory=.*|WorkingDirectory=$PROJECT_DIR|g" \
    -e "s|ExecStart=.*|ExecStart=$PROJECT_DIR/venv/bin/python web_server.py|g" \
    -e "s|ReadWritePaths=.*|ReadWritePaths=$PROJECT_DIR|g" \
    "$WEB_SERVICE_FILE" > "$TMP_WEB_SERVICE"

sudo cp "$TMP_WEB_SERVICE" "$WEB_SYSTEMD_PATH"
rm "$TMP_WEB_SERVICE"

# Configure tunnel service
TUNNEL_SERVICE_FILE="$PROJECT_DIR/valorant-tunnel.service"
TUNNEL_SYSTEMD_PATH="/etc/systemd/system/valorant-tunnel.service"
TMP_TUNNEL_SERVICE=$(mktemp)
sed \
    -e "s|User=kartiksakhuja02|User=$CURRENT_USER|g" \
    -e "s|Group=kartiksakhuja02|Group=$CURRENT_USER|g" \
    "$TUNNEL_SERVICE_FILE" > "$TMP_TUNNEL_SERVICE"

sudo cp "$TMP_TUNNEL_SERVICE" "$TUNNEL_SYSTEMD_PATH"
rm "$TMP_TUNNEL_SERVICE"

# Reload systemd and enable services
sudo systemctl daemon-reload

sudo systemctl enable "$SERVICE_NAME"
sudo systemctl restart "$SERVICE_NAME"

sudo systemctl enable valorant-web
sudo systemctl restart valorant-web

sudo systemctl enable valorant-tunnel
sudo systemctl restart valorant-tunnel

echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║              ✅  Setup complete!                 ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""
echo "  Bot status:    sudo systemctl status $SERVICE_NAME"
echo "  Web status:    sudo systemctl status valorant-web"
echo "  Tunnel status: sudo systemctl status valorant-tunnel"
echo "  Bot logs:      journalctl -u $SERVICE_NAME -f"
echo "  Web logs:      journalctl -u valorant-web -f"
echo "  Tunnel logs:   journalctl -u valorant-tunnel -f"
echo ""


