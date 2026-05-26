# TeleBridge

Multi-account Telegram message relay hub with n8n webhook integration.

## Quick Start

```bash
cd Telegram_Message_Monitor
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Open http://localhost:8000

## Docker

```bash
docker build -t telebridge .
docker run -p 8000:8000 -v telebridge_data:/app/data telebridge
```

## Coolify Deploy

1. Push to GitHub
2. Coolify → New Project → Deploy from GitHub → select repo
3. Set `APP_URL` env var to your domain
4. Deploy (no other env vars needed — SECRET_KEY auto-generates)

## Setup

1. Go to **Settings** → add your Telegram API ID & Hash (from https://my.telegram.org/apps)
2. **Accounts** → add Bot (via @BotFather token) or User Account (via phone)
3. **Rules** → create forward rule: source chat → destination chat
4. Optionally add n8n webhook URL for passthrough or destination-only mode

## Features

- Multiple Telegram accounts (bots + user accounts via MTProto)
- Forward messages between any chats/groups/channels
- n8n webhook integration (passthrough + destination modes)
- Real-time message forwarding with background workers
- Forward logs and activity dashboard
- Zero external dependencies (SQLite, no Redis)
