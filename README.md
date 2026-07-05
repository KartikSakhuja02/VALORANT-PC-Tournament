# 🎯 VALORANT PC Tournament — Discord Bot & Verification Server

A Discord bot for managing VALORANT PC tournaments, integrated with a FastAPI verification server and a React confirmation frontend. Designed to run 24/7 on a **Raspberry Pi** via systemd.

---

## 📂 Project Structure

```
VALORANT PC Tournament/
├── bot.py                  ← Discord bot entry point
├── web_server.py           ← FastAPI web server (port 8080)
├── mailer.py               ← Gmail API email sender & HTML template
├── db.py                   ← asyncpg connection pool helper
├── config.py               ← Configuration loader
├── schema.sql              ← PostgreSQL DB tables & structures
├── requirements.txt        ← Python dependencies
├── .env.example            ← Secret configuration template
├── .gitignore
├── valorant-bot.service    ← systemd service for the Discord bot
├── valorant-web.service    ← systemd service for the FastAPI server
├── setup.sh                ← Automated dependency installer for Raspberry Pi
├── gmail_setup.py          ← Gmail API OAuth token builder helper
├── static/                 ← Compiled React frontend files
└── confirmation-frontend/  ← Source React Vite code (Vite + Tailwind v4)
```

---

## 🔧 Step 1 — Discord Developer Portal

1. Go to **https://discord.com/developers/applications** and create an application.
2. Under the **Bot** tab, click **Add Bot** and copy the **Bot Token**.
3. Enable these **Privileged Gateway Intents**:
   - ✅ Server Members Intent
   - ✅ Message Content Intent
4. Save Changes.
5. Generate the invite URL under OAuth2 -> URL Generator:
   * Scopes: `bot`, `applications.commands`
   * Permissions: `Administrator` (or *Manage Roles*, *Manage Channels*, *Send Messages*, *Embed Links*, *Read Message History*, *Use Slash Commands*).

---

## 📧 Step 2 — Gmail API Integration (One-time Setup)

We send the confirmation email using Google's official Gmail API.

1. Go to the **[Google Cloud Console](https://console.cloud.google.com/)**.
2. Create a new Cloud Project.
3. Search for **Gmail API** in the API Library and click **Enable**.
4. Configure the **OAuth Consent Screen**:
   - User Type: **External**
   - Publishing status: Keep in **Testing**
   - Add your email address to the **Test Users** list.
5. Create Credentials:
   - Go to Credentials -> **Create Credentials** -> **OAuth Client ID**.
   - Application type: **Desktop app**.
   - Name it `VCT Bot`. Click Create.
6. Click the download icon next to your client ID to download the client secrets JSON.
7. Rename the downloaded file to `credentials.json` and place it in the project root directory.
8. Run the setup script locally to authenticate:
   ```bash
   python gmail_setup.py
   ```
   *This opens a browser window where you log in with your authorized test Gmail account. It generates `token.json` which is used by the Pi to send emails 24/7 without needing user interaction.*

---

## ☁️ Step 3 — Cloudflare Tunnel Setup (Public HTTPS URL)

To allow remote players to confirm their emails without exposing your Pi's database or home network:

1. Install `cloudflared` on your Raspberry Pi:
   ```bash
   sudo mkdir -p --mode=0755 /usr/share/keyrings
   curl -fsSL https://pkg.cloudflare.com/cloudflare.gpg | sudo gpg --dearmor -o /usr/share/keyrings/cloudflare-gkeyring.gpg
   echo "deb [signed-by=/usr/share/keyrings/cloudflare-gkeyring.gpg] https://pkg.cloudflare.com/cloudflared Bullseye main" | sudo tee /etc/apt/sources.list.d/cloudflared.list
   sudo apt-get update && sudo apt-get install cloudflared
   ```
2. Start a free quick tunnel to test it:
   ```bash
   cloudflared tunnel --url http://localhost:8080
   ```
3. Copy the generated `.trycloudflare.com` URL (e.g., `https://vct-confirm.trycloudflare.com`) and paste it as `CONFIRMATION_SERVER_URL` in your `.env`.

---

## ⚙️ Step 4 — Configure `.env`

Copy `.env.example` to `.env` and fill in:

```ini
DISCORD_TOKEN=your_bot_token
GUILD_ID=your_discord_server_id
REGISTRATION_CHANNEL_ID=your_registration_channel_id
MOD_ROLE_ID=your_moderator_role_id

DB_HOST=localhost
DB_PORT=5432
DB_NAME=valorant_pc_tournament
DB_USER=vct_bot
DB_PASSWORD=your_db_password

CONFIRMATION_SERVER_URL=https://your-cloudflare-subdomain.trycloudflare.com
GMAIL_SENDER=your-email@gmail.com
```

---

## 💻 Step 5a — Local Development

```bash
# 1. Start Python venv and install requirements
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Linux/Mac

pip install -r requirements.txt

# 2. Build Vite React frontend
cd confirmation-frontend
npm install
npm run build                  # Compiles files directly to ../static/
cd ..

# 3. Run Bot & Server in separate terminals
python bot.py
uvicorn web_server:app --port 8080 --reload
```

---

## 🥧 Step 5b — Deploy to Raspberry Pi (24/7)

### SCP Transfer
Transfer files to the Pi path `/home/kartiksakhuja02/Documents/ValorantPCTournament/`:
```bash
scp -r "VALORANT PC Tournament/" kartiksakhuja02@<PI_IP>:/home/kartiksakhuja02/Documents/ValorantPCTournament
```

### Installation
Run the automated installation script:
```bash
ssh kartiksakhuja02@<PI_IP>
cd ~/Documents/ValorantPCTournament
chmod +x setup.sh
./setup.sh
```

### Enable Services
Once setup finishes, enable the background services:
```bash
# Register services
sudo cp valorant-bot.service /etc/systemd/system/
sudo cp valorant-web.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Start and enable on boot
sudo systemctl enable --now valorant-bot
sudo systemctl enable --now valorant-web
```

---

## 🛠️ Pi Services Management

```bash
# Check running status
sudo systemctl status valorant-bot
sudo systemctl status valorant-web

# Restart services after a code update
sudo systemctl restart valorant-bot
sudo systemctl restart valorant-web

# View real-time output logs
journalctl -u valorant-bot -f
journalctl -u valorant-web -f
```

---

## 📜 Available Bot Commands

| Command | Scope | Description |
|---|---|---|
| `/ping` | Global | Verifies bot gateway response, REST latency, and connection quality |
| (Panel Button) | Channel | Spawns a registration thread for team captains |
