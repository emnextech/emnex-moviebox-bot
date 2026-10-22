# Owner and Developer Guide

This is the full operations guide for the person deploying, maintaining, and administering the Telegram Movie Download Bot.

It covers:

- what the bot does
- what you need before launch
- how to deploy on DigitalOcean
- how to configure the bot
- how to use owner commands
- how to maintain and troubleshoot the service

## 1. What This Bot Does

The bot has two user tiers:

- BASIC users search in Telegram and get redirected to your website.
- PRO users get direct worker-backed download links inside Telegram.

For TV shows:

- users can choose a season
- browse episodes in chunks
- PRO users can request direct links for the current chunk

The bot does not host or download media. It only talks to the worker API and returns the resulting links.

## 2. Main Components

- Telegram bot in `bot/`
- Worker API in `worker/`
- Website used for BASIC redirects
- Supabase for users, plan expiry, and event logs

## 3. Before You Deploy

You need the following:

- a Telegram bot token from BotFather
- a running worker API URL
- a worker API key
- a website URL for BASIC redirects
- a Supabase project
- the Supabase service role key
- at least one Telegram user ID that will be the owner/admin

## 4. Environment Variables

The bot reads these values from `bot/.env`:

- `BOT_TOKEN`
- `BOT_NAME`
- `BRAND_NAME`
- `SUPPORT_CONTACT`
- `WORKER_API_BASE`
- `WORKER_API_KEY`
- `SITE_BASE_URL`
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `BOT_OWNER_IDS`
- `MAX_BULK_EPISODES`
- `MAX_SEARCH_RESULTS`
- `SEARCH_COOLDOWN_SECONDS`
- `SOURCE_COOLDOWN_SECONDS`
- `BULK_COOLDOWN_SECONDS`
- `SOURCE_CONCURRENCY`
- `WORKER_TIMEOUT_SECONDS`

Use [bot/.env.example](/c:/Users/LENOVO/OneDrive/Desktop/Emnex/projects/emnexmovie/bot/.env.example) as the template.

## 5. Supabase Setup

Run the SQL in [bot/db/schema.sql](/c:/Users/LENOVO/OneDrive/Desktop/Emnex/projects/emnexmovie/bot/db/schema.sql) inside the Supabase SQL editor.

This creates:

- `telegram_users`
- `telegram_events`

Behavior to know:

- New users are created automatically on first interaction.
- If a PRO user expires, the bot downgrades them back to BASIC during later lookups and interactions.

## 6. Recommended DigitalOcean Setup

This bot is a long-polling Python process, so it works well on a small Droplet.

Recommended starting point:

- Droplet type: regular Droplet
- OS: Ubuntu LTS
- Size: Basic shared CPU, 1 GB RAM minimum for a small bot
- Backups: enable if the bot is business critical
- Monitoring: enable
- IPv6: optional but safe to enable
- Authentication: SSH keys, not password login

Recommended security baseline:

- use SSH keys
- create a firewall that allows SSH only
- keep the bot as a non-root service
- store secrets only in `bot/.env`

## 7. DigitalOcean Deployment Step By Step

### Step 1: Create the Droplet

In the DigitalOcean control panel:

1. Create a new Droplet.
2. Choose Ubuntu LTS.
3. Choose a small basic plan to start.
4. Select your region.
5. Enable monitoring.
6. Add your SSH key.
7. Create the Droplet.

If you use a cloud firewall, allow inbound SSH only.

### Step 2: Connect to the server

SSH into the Droplet:

```bash
ssh root@YOUR_DROPLET_IP
```

If you prefer, you can use the DigitalOcean browser console instead.

### Step 3: Update the server

```bash
apt update && apt upgrade -y
apt install -y git python3 python3-venv python3-pip ufw
```

Optional firewall setup:

```bash
ufw allow OpenSSH
ufw enable
ufw status
```

### Step 4: Create an app user

Running the bot as a dedicated user is cleaner than using `root`.

```bash
adduser botadmin
usermod -aG sudo botadmin
```

Then switch:

```bash
su - botadmin
```

### Step 5: Upload or clone the project

If the code is in Git:

```bash
git clone YOUR_REPO_URL emnexmovie
cd emnexmovie
```

If not, upload the project folder with SFTP or Git first, then enter the repo directory.

### Step 6: Create the Python environment

From the repo root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r bot/requirements.txt
```

### Step 7: Create the bot environment file

```bash
cp bot/.env.example bot/.env
nano bot/.env
```

Fill in all real values.

Minimum production values:

```env
BOT_TOKEN=your_bot_token
BOT_NAME=Your Brand Bot
BRAND_NAME=Your Brand
SUPPORT_CONTACT=@your_support_username
WORKER_API_BASE=https://your-worker-domain.com
WORKER_API_KEY=your_worker_key
SITE_BASE_URL=https://your-site-domain.com
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key
BOT_OWNER_IDS=123456789
MAX_BULK_EPISODES=10
MAX_SEARCH_RESULTS=8
SEARCH_COOLDOWN_SECONDS=3
SOURCE_COOLDOWN_SECONDS=2
BULK_COOLDOWN_SECONDS=10
SOURCE_CONCURRENCY=3
WORKER_TIMEOUT_SECONDS=20
```

### Step 8: Apply the database schema

Open Supabase and run [bot/db/schema.sql](/c:/Users/LENOVO/OneDrive/Desktop/Emnex/projects/emnexmovie/bot/db/schema.sql).

You only need to do this once per database.

### Step 9: Test the bot manually

From the repo root:

```bash
source .venv/bin/activate
python -m bot.main
```

Now test in Telegram:

1. Send `/start`
2. Send `/plan`
3. Search for a movie
4. Search for a TV show
5. Test a BASIC redirect
6. Test an owner command

Stop the bot with `Ctrl+C` after confirming it works.

### Step 10: Run the bot with systemd

Create the service file:

```bash
sudo nano /etc/systemd/system/emnex-bot.service
```

Paste:

```ini
[Unit]
Description=Emnex Telegram Movie Bot
After=network.target

[Service]
Type=simple
User=botadmin
WorkingDirectory=/home/botadmin/emnexmovie
ExecStart=/home/botadmin/emnexmovie/.venv/bin/python -m bot.main
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Then enable and start it:

```bash
sudo systemctl daemon-reload
sudo systemctl enable emnex-bot
sudo systemctl start emnex-bot
sudo systemctl status emnex-bot
```

### Step 11: View logs

```bash
sudo journalctl -u emnex-bot -f
```

Useful commands:

```bash
sudo systemctl restart emnex-bot
sudo systemctl stop emnex-bot
sudo systemctl status emnex-bot
```

## 8. How The Owner Uses The Bot

Owner/admin commands:

- `/grant <user_id> <days>`
- `/revoke <user_id>`
- `/user <user_id>`
- `/stats`

These commands work only:

- in private chat
- for Telegram IDs listed in `BOT_OWNER_IDS`

### Typical owner workflow

1. User pays for PRO.
2. User sends `/plan` to get their Telegram user ID.
3. Owner runs:

```text
/grant <user_id> <days>
```

4. User becomes PRO immediately.

### Remove PRO access

```text
/revoke <user_id>
```

### Check a user

```text
/user <user_id>
```

### View basic stats

```text
/stats
```

## 9. How BASIC And PRO Work

### BASIC

- Search in Telegram
- View available qualities
- Open your website for downloads

Movie redirect pattern:

```text
/movie/{id}?ref=telegram&tier=basic&quality={quality}#download-section
```

TV redirect pattern:

```text
/watch/{id}?season={season}&episode={episode}&ref=telegram&tier=basic
```

### PRO

- Receive direct download buttons in Telegram
- For TV shows, get direct links per episode
- For bulk delivery, receive links for the current episode chunk

## 10. Updating The Bot

When you deploy a new version:

```bash
cd /home/botadmin/emnexmovie
git pull
source .venv/bin/activate
pip install -r bot/requirements.txt
sudo systemctl restart emnex-bot
sudo systemctl status emnex-bot
```

After restart, test:

- `/start`
- `/plan`
- one movie search
- one TV search
- one owner command

## 11. Launch Checklist For A New Client

1. Create the bot in BotFather.
2. Get the bot token.
3. Set `BOT_NAME`, `BRAND_NAME`, and `SUPPORT_CONTACT`.
4. Set `SITE_BASE_URL`.
5. Set `WORKER_API_BASE` and `WORKER_API_KEY`.
6. Add the owner Telegram ID to `BOT_OWNER_IDS`.
7. Apply the Supabase schema if using a new database.
8. Start the bot.
9. Test both BASIC and PRO behavior.
10. Hand over [bot/CLIENT-HANDOFF.md](/c:/Users/LENOVO/OneDrive/Desktop/Emnex/projects/emnexmovie/bot/CLIENT-HANDOFF.md) to the client.

## 12. Troubleshooting

### The bot does not start

Check:

- `bot/.env` exists
- all required env vars are set
- dependencies installed successfully
- the Python virtual environment exists
- `python -m bot.main` works when run manually

### Owner commands say owner-only

Check:

- the correct Telegram numeric ID is in `BOT_OWNER_IDS`
- the command is being used in private chat
- there are no spaces or invalid characters in the env value

### BASIC links open the wrong website

Check:

- `SITE_BASE_URL`
- your website routes
- [bot/utils/buttons.py](/c:/Users/LENOVO/OneDrive/Desktop/Emnex/projects/emnexmovie/bot/utils/buttons.py)

### PRO links are missing

Check:

- the worker is online
- the worker API key is correct
- the selected title has sources
- the worker is not returning `noSources`

### TV seasons or episodes are missing

Check:

- the worker detail endpoint returns valid `seasons`
- each season has a usable episode count

### The service keeps restarting

Check:

- `sudo journalctl -u emnex-bot -f`
- invalid `.env` values
- bad network access to Supabase or the worker
- wrong file paths in the systemd service

## 13. Security And Operations Notes

- Do not commit `bot/.env`.
- Treat the Supabase service role key as a secret.
- Treat the worker API key as a secret.
- Use SSH keys instead of password login.
- Use a firewall that only exposes SSH inbound.
- Keep the server updated with security patches.
- Back up your env file securely.

## 14. Recommended DigitalOcean Reading

I based the deployment guidance above on official DigitalOcean documentation. These are good references when you want the platform-specific details:

- Droplet Quickstart: https://docs.digitalocean.com/products/droplets/getting-started/quickstart/
- Set up a Production-Ready Droplet: https://docs.digitalocean.com/products/droplets/getting-started/recommended-droplet-setup/
- Droplet Console: https://docs.digitalocean.com/products/droplets/how-to/connect-with-console/
- Create Firewalls: https://docs.digitalocean.com/products/networking/firewalls/how-to/create/
- Manage SSH Keys on Teams: https://docs.digitalocean.com/platform/teams/how-to/upload-ssh-keys/

## 15. Summary

This bot is simple to operate once deployed:

- configure the env
- start the service
- grant PRO manually
- monitor logs
- update with `git pull` and service restart

For clients, the short handoff doc is [bot/CLIENT-HANDOFF.md](/c:/Users/LENOVO/OneDrive/Desktop/Emnex/projects/emnexmovie/bot/CLIENT-HANDOFF.md).
