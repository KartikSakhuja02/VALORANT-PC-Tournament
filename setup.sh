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

# ── 5. Install & enable systemd service ──────────────────────────────────────
echo "▶ [5/5] Installing systemd service..."

# Patch the service file paths to match the current directory and user
CURRENT_USER="$(whoami)"
TMP_SERVICE=$(mktemp)

sed \
    -e "s|User=pi|User=$CURRENT_USER|g" \
    -e "s|Group=pi|Group=$CURRENT_USER|g" \
    -e "s|WorkingDirectory=.*|WorkingDirectory=$PROJECT_DIR|g" \
    -e "s|ExecStart=.*|ExecStart=$PROJECT_DIR/venv/bin/python bot.py|g" \
    -e "s|ReadWritePaths=.*|ReadWritePaths=$PROJECT_DIR|g" \
    "$SERVICE_FILE" > "$TMP_SERVICE"

sudo cp "$TMP_SERVICE" "$SYSTEMD_PATH"
rm "$TMP_SERVICE"

sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE_NAME"
sudo systemctl restart "$SERVICE_NAME"

echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║              ✅  Setup complete!                 ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""
echo "  Service status:  sudo systemctl status $SERVICE_NAME"
echo "  Live logs:       journalctl -u $SERVICE_NAME -f"
echo "  Restart bot:     sudo systemctl restart $SERVICE_NAME"
echo ""
