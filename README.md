# TeleBridge

Multi-account Telegram message relay with n8n webhook integration.

## Quick Start

```bash
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Open http://localhost:8000

## Docker

```bash
docker build -t telebridge .
docker run -p 8000:8000 -v telebridge_data:/app/data telebridge
```

## Setup

1. Settings → add Telegram API ID & Hash (from https://my.telegram.org/apps)
2. Accounts → add Bot (bot token) or User Account (phone)
3. Rules → create forward rule: source → destination
4. Optionally add n8n webhook URL

## Features

- Multiple Telegram accounts (bots + MTProto user accounts)
- Forward messages between any chats/groups/channels
- Content filters (keywords, media types, user allow/block, schedule, cooldown)
- Delivery agent/method split (account, bot, fallback)
- n8n webhook integration (passthrough, destination modes)
- Activity dashboard with forward logs

## Deploy

Push to GitHub → Coolify → New Project → Deploy from GitHub → done.
SECRET_KEY auto-generates — no env vars required.
