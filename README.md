# 🎯 VALORANT PC Tournament — Discord Bot

A Discord bot for managing VALORANT PC tournaments, built with **Python** (`discord.py 2.x`) and designed to run 24/7 on a **Raspberry Pi** via systemd.

---

## 📂 Project Structure

```
VALORANT PC Tournament/
├── bot.py                  ← Main bot entry point
├── config.py               ← Environment/config loader
├── requirements.txt        ← Python dependencies
├── .env.example            ← Secret template (copy → .env)
├── .env                    ← Your actual secrets (DO NOT commit)
├── .gitignore
├── valorant-bot.service    ← systemd unit for the Raspberry Pi
├── setup.sh                ← One-shot Pi setup script
└── bot.log                 ← Runtime log (auto-created)
```

---

## 🔧 Step 1 — Create the Discord Application & Bot

1. Go to **https://discord.com/developers/applications**
2. Click **"New Application"** — name it `VALORANT Tournament Bot`
3. Go to the **"Bot"** tab on the left sidebar
4. Click **"Add Bot"** — confirm
5. Under **"Token"** click **"Reset Token"** and **copy it** (you'll need this)
6. Enable these **Privileged Gateway Intents**:
   - Server Members Intent
   - Message Content Intent
7. Click **Save Changes**

---

## 🔗 Step 2 — Invite the Bot to Your Server

Use this URL (replace `YOUR_CLIENT_ID` with the Application ID from the "General Information" tab):

```
https://discord.com/oauth2/authorize?client_id=YOUR_CLIENT_ID&scope=bot+applications.commands&permissions=8
```

> **Permissions breakdown** — `permissions=8` is **Administrator**.
> For a tighter permission set use: `permissions=2147560512`
> (Manage Roles + Manage Channels + Send Messages + Embed Links + Read Message History + Use Slash Commands)

---

## ⚙️ Step 3 — Configure Your .env

```bash
cp .env.example .env
nano .env   # or open in any text editor
```

| Variable | Where to find it |
|---|---|
| `DISCORD_TOKEN` | Bot tab → Token (Step 1) |
| `GUILD_ID` | Right-click your server icon → Copy Server ID (enable Developer Mode in Discord Settings → Advanced) |
| `LOG_CHANNEL_ID` | Optional — right-click a text channel → Copy Channel ID |

---

## 💻 Step 4a — Run Locally (for testing)

```bash
# Create a virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Mac/Linux

# Install dependencies
pip install -r requirements.txt

# Run the bot
python bot.py
```

---

## 🥧 Step 4b — Deploy to Raspberry Pi (24/7)

### Transfer files to the Pi

```bash
# From your Windows machine (using SCP)
scp -r "VALORANT PC Tournament/" pi@<PI_IP_ADDRESS>:/home/pi/valorant-bot
```

Or clone from Git if you have a repo.

### Run the setup script

```bash
ssh pi@<PI_IP_ADDRESS>
cd /home/pi/valorant-bot
chmod +x setup.sh
./setup.sh
```

The script will:
1. Install system dependencies
2. Create a Python virtual environment
3. Install all Python packages
4. Prompt you to fill in `.env`
5. Install, enable, and start the systemd service

---

## 🛠️ Pi Service Management

```bash
# Check if the bot is running
sudo systemctl status valorant-bot

# Start / Stop / Restart
sudo systemctl start   valorant-bot
sudo systemctl stop    valorant-bot
sudo systemctl restart valorant-bot

# Watch live logs
journalctl -u valorant-bot -f
```

---

## 📜 Available Slash Commands

| Command | Description |
|---|---|
| `/ping` | Shows WebSocket latency, REST round-trip, connection quality, and bot uptime |

---

## 🚀 Adding More Commands (Cogs)

```
cogs/
├── registration.py   ← /register, /team
├── bracket.py        ← /bracket, /score
└── admin.py          ← /announce, /kick-team
```

Load them in `bot.py`:

```python
await bot.load_extension("cogs.registration")
```
