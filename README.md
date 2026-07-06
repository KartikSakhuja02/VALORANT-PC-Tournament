# 🎯 VALORANT PC Tournament — Discord Bot & Verification Portal

A Discord bot for managing VALORANT PC tournaments, built with **Python** (`discord.py 2.x`, `FastAPI`), featuring dynamic email verification using **Google App Passwords** and designed to run 24/7 on a **Raspberry Pi** via systemd and Cloudflare Tunnels.

---

## 📂 Project Structure

```
VALORANT PC Tournament/
├── bot.py                  ← Discord bot entry point
├── config.py               ← Environment/config loader
├── db.py                   ← DB connection pool
├── mailer.py               ← SMTP async mailer & inlined email template
├── web_server.py           ← FastAPI verification site (port 8080)
├── schema.sql              ← PostgreSQL DB schema
├── requirements.txt        ← Python dependencies
├── .env.example            ← Secret template
├── .env                    ← Your actual secrets (DO NOT commit)
├── .gitignore
├── valorant-bot.service    ← Bot systemd configuration
├── valorant-web.service    ← FastAPI systemd configuration
└── setup.sh                ← One-shot Pi setup script
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

---

## 📧 Step 3 — Get Google App Password

Since we are using SMTP to send confirmation emails securely from your Gmail account:
1. Go to your **Google Account settings** (https://myaccount.google.com/).
2. Navigate to **Security**.
3. Under *How you sign in to Google*, select **2-Step Verification** (must be enabled first).
4. Scroll to the bottom and select **App passwords**.
5. Select **Other (Custom name)**, type `VALORANT Bot`, and click **Generate**.
6. Copy the **16-character code** (no spaces). This goes to `SMTP_PASSWORD` in `.env`.

---

## ⚙️ Step 4 — Configure Your `.env`

```bash
cp .env.example .env
nano .env
```

| Variable | Value / Where to find it |
|---|---|
| `DISCORD_TOKEN` | Bot tab → Token (Step 1) |
| `GUILD_ID` | Server ID |
| `REGISTRATION_CHANNEL_ID` | Channel ID where the persistent registration panel will reside |
| `MOD_ROLE_ID` | Role ID of tournament moderators (added to private registration threads) |
| `SMTP_EMAIL` | Your Gmail address |
| `SMTP_PASSWORD` | The 16-character App Password (Step 3) |
| `CONFIRMATION_SERVER_URL` | The public HTTPS address of your Cloudflare Tunnel (Step 6) |

---

## 🥧 Step 5 — Deploy to Raspberry Pi (24/7)

### Transfer files to the Pi
```bash
# From your Windows machine (replace with actual Pi username and IP)
scp -r "VALORANT PC Tournament/" kartiksakhuja02@<PI_IP_ADDRESS>:/home/kartiksakhuja02/Documents/ValorantPCTournament
```

### Run the setup script
```bash
ssh kartiksakhuja02@<PI_IP_ADDRESS>
cd ~/Documents/ValorantPCTournament
chmod +x setup.sh
./setup.sh
```
The script installs Python packages, sets up a virtual environment, creates a template `.env`, and registers both `valorant-bot` and `valorant-web` services in systemd to run 24/7.

---

## 🌐 Step 6 — Expose Web Server via Cloudflare Tunnel

Since the verification portal runs on the Pi (`http://localhost:8080`), you can make it public securely and for free with Cloudflare:
1. **Install cloudflared on Pi:**
   ```bash
   sudo mkdir -p --mode=0755 /usr/share/keyrings
   curl -fsSL https://pkg.cloudflare.com/cloudflare.gpg | sudo gpg --dearmor -o /usr/share/keyrings/cloudflare-gkeyring.gpg
   echo "deb [signed-by=/usr/share/keyrings/cloudflare-gkeyring.gpg] https://pkg.cloudflare.com/cloudflared Bullseye main" | sudo tee /etc/apt/sources.list.d/cloudflared.list
   sudo apt-get update && sudo apt-get install cloudflared
   ```
2. **Start a free tunnel:**
   ```bash
   cloudflared tunnel --url http://localhost:8080
   ```
3. Copy the outputted `https://*.trycloudflare.com` URL and put it in your `.env` as `CONFIRMATION_SERVER_URL`. Restart the bot afterwards.

---

## 🛠️ Pi Service Management

```bash
# Check status of Bot and Web Server
sudo systemctl status valorant-bot
sudo systemctl status valorant-web

# Restart services
sudo systemctl restart valorant-bot
sudo systemctl restart valorant-web

# Live logs
journalctl -u valorant-bot -f
journalctl -u valorant-web -f
```
