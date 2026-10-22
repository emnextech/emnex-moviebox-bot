# Telegram Movie Download Bot v1

Reusable `aiogram` 3 Telegram bot for movie and TV discovery with a BASIC tier and a PRO tier.

Related docs:

- [CLIENT-HANDOFF.md](/c:/Users/LENOVO/OneDrive/Desktop/Emnex/projects/emnexmovie/bot/CLIENT-HANDOFF.md)
- [OWNER-DEVELOPER-GUIDE.md](/c:/Users/LENOVO/OneDrive/Desktop/Emnex/projects/emnexmovie/bot/OWNER-DEVELOPER-GUIDE.md)

This bot is designed as a sellable system:

- BASIC users search titles and get redirected to your website for downloads.
- PRO users receive direct download links inside Telegram.
- TV shows support season browsing, episode paging, and bulk link delivery for the current chunk.
- Supabase stores users, plan expiry, and activity logs.
- One codebase can be branded and deployed for multiple clients.

## What This Bot Does

### BASIC users

- Search movies and TV shows in Telegram
- Open a result and see available quality options
- Click a quality button and land on your website
- Monetize with ads, popups, affiliate links, or other website funnels

### PRO users

- Search movies and TV shows in Telegram
- Receive direct worker-backed download links inside Telegram
- Access 1080p when the source exists
- For TV shows, select a season, choose an episode, or get links for the current episode chunk
- No website redirect for download delivery

## Product Model

This project supports three roles:

1. Developer / operator
   You install, brand, deploy, and maintain the bot.
2. Client / bot owner
   The person who owns the branded bot and uses admin commands to manage PRO access.
3. End user
   The Telegram user who searches and downloads content through the bot.

## Architecture

Core flow:

`Telegram Bot -> Worker API -> Telegram UI or Website Redirect`

Main components:

- Telegram bot in `bot/`
- Existing movie worker API in `worker/`
- Existing website used for BASIC redirects
- Supabase Postgres for users and event logs
- In-memory rate limiting inside the bot process

The bot never downloads or stores media files. It only fetches metadata and direct source links from the worker API, then sends those links to the user.

## Supported Worker API Endpoints

The bot expects these endpoints to already exist and stay compatible:

- `GET /api/search/:query`
- `GET /api/movie/:id`
- `GET /api/sources/:id`
- `GET /api/sources/:id?season=&episode=`

The bot sends the worker API key through the `X-Api-Key` header.

## Bot Features

- `aiogram` 3 based Telegram bot
- Private chat only
- Free-text search and `/search <title>`
- Movie and TV result handling
- Season and episode browsing
- Bulk episode delivery for the current page chunk
- BASIC vs PRO plan enforcement
- Automatic expiry downgrade on next interaction
- Owner-only admin commands
- Event logging for analytics and troubleshooting
- Config-driven branding for reuse across clients

## Project Layout

```text
bot/
  main.py
  requirements.txt
  .env.example
  README.md
  config/
    settings.py
  commands/
    start.py
    search.py
    admin.py
  handlers/
    movie_handler.py
    tv_handler.py
    quality_handler.py
    helpers.py
  services/
    api_client.py
    user_service.py
    rate_limiter.py
  utils/
    buttons.py
    callbacks.py
    formatter.py
  db/
    schema.sql
```

## How The User Flow Works

### Movie flow

1. User sends a title like `John Wick`
2. Bot calls `GET /api/search/:query`
3. Bot shows matching titles as Telegram buttons
4. User taps a title
5. Bot calls `GET /api/movie/:id`
6. Bot calls `GET /api/sources/:id`
7. Bot shows available quality and variant buttons

For BASIC users:

- Quality buttons open:
  - `SITE_BASE_URL/movie/{id}?ref=telegram&tier=basic&quality={quality}#download-section`

For PRO users:

- Quality buttons trigger callbacks
- Bot resolves direct links from `processedSources`
- Bot replies with Telegram URL buttons for the selected variant

### TV flow

1. User searches for a TV show
2. Bot displays the show result
3. User taps the show
4. Bot shows available seasons from worker `seasons`
5. User taps a season
6. Bot shows episode buttons in pages of `MAX_BULK_EPISODES`
7. User can:
   - choose one episode
   - use `Select All Episodes` for the current page chunk

For BASIC users:

- Single-episode quality buttons open:
  - `SITE_BASE_URL/watch/{id}?season={season}&episode={episode}&ref=telegram&tier=basic`

For PRO users:

- Single episode:
  - bot resolves worker sources for the selected episode
  - bot returns direct download buttons for the chosen variant
- Bulk page chunk:
  - bot samples the current chunk
  - user chooses a quality variant
  - bot resolves links for each episode in that chunk with bounded concurrency
  - bot returns one Telegram URL button per episode that resolved successfully

### Variant handling

If the worker exposes multiple variants for the same quality, such as different audio tracks, the bot keeps them separate. It does not guess which one the user wants.

Example:

- `720p - English`
- `720p - Hindi`
- `1080p - English`

## Developer Guide

This section is for you, the developer or operator building and deploying the bot.

### Prerequisites

- Python 3.11 or newer recommended
- A Telegram bot token from BotFather
- A working worker API deployment
- A working website deployment for BASIC redirects
- A Supabase project
- The Supabase service role key

### 1. Install dependencies

From the repository root:

```bash
python -m venv .venv
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r bot/requirements.txt
```

Linux or macOS:

```bash
source .venv/bin/activate
pip install -r bot/requirements.txt
```

### 2. Create the environment file

Copy the example file:

```bash
cp bot/.env.example bot/.env
```

On Windows PowerShell:

```powershell
Copy-Item bot/.env.example bot/.env
```

Then edit `bot/.env` with real values.

### 3. Environment variables

Required:

- `BOT_TOKEN`
  Telegram bot token from BotFather.
- `WORKER_API_BASE`
  Base URL for the worker API, for example `https://server.example.com`
- `WORKER_API_KEY`
  API key expected by the worker.
- `SITE_BASE_URL`
  Public website URL used for BASIC redirects.
- `SUPABASE_URL`
  Your Supabase project URL.
- `SUPABASE_SERVICE_ROLE_KEY`
  Service role key used by the bot to read and write users and logs.
- `BOT_OWNER_IDS`
  Comma-separated Telegram user IDs allowed to run owner commands.

Optional branding and runtime settings:

- `BOT_NAME`
  Display name used in messages.
- `BRAND_NAME`
  Brand label for your business or the client brand.
- `SUPPORT_CONTACT`
  Telegram username or contact text shown to users for upgrades or support.
- `MAX_BULK_EPISODES`
  Number of episodes shown per page and bulk request cap.
- `MAX_SEARCH_RESULTS`
  Max search results shown to the user.
- `SEARCH_COOLDOWN_SECONDS`
  Cooldown for title searches.
- `SOURCE_COOLDOWN_SECONDS`
  Cooldown for detail and source lookups.
- `BULK_COOLDOWN_SECONDS`
  Cooldown for bulk episode delivery.
- `SOURCE_CONCURRENCY`
  Max concurrent worker source requests during bulk delivery.
- `WORKER_TIMEOUT_SECONDS`
  Timeout for worker API calls.

### 4. Configure Supabase

Open the Supabase SQL editor and apply [schema.sql](/c:/Users/LENOVO/OneDrive/Desktop/Emnex/projects/emnexmovie/bot/db/schema.sql).

This creates:

- `telegram_users`
  stores Telegram identity, plan, expiry, and last seen timestamp
- `telegram_events`
  stores bot actions for analytics and auditing

Important notes:

- The bot uses the service role key, so do not expose it anywhere public.
- The code automatically inserts new users on first interaction.
- If a user had `plan = pro` but the expiry passed, the bot downgrades them back to `basic` on the next lookup or interaction.

### 5. Run the bot locally

From the repository root:

```bash
python -m bot.main
```

The bot uses long polling, not Telegram webhooks.

### 6. First-time smoke test

After launching the bot:

1. Open the bot in Telegram
2. Send `/start`
3. Send `/plan`
4. Search for a movie title
5. Tap a result
6. Confirm that:
   - BASIC user buttons open the website
   - PRO logic is enforced correctly
   - TV seasons and episodes display correctly

### 7. Owner admin commands

These commands only work in private chat and only for Telegram IDs listed in `BOT_OWNER_IDS`.

- `/grant <user_id> <days>`
  Grant PRO access until now plus the given number of days.
- `/revoke <user_id>`
  Remove PRO access immediately.
- `/user <user_id>`
  Inspect a user record.
- `/stats`
  View total users, active PRO users, and events in the last 24 hours.

Examples:

```text
/grant 123456789 30
/revoke 123456789
/user 123456789
/stats
```

### 8. How PRO activation works

The current v1 activation model is manual:

1. User contacts support or pays externally
2. Owner gets the Telegram user ID
3. Owner runs:

```text
/grant <user_id> <days>
```

4. The user becomes PRO immediately
5. When expiry is reached, the bot automatically falls back to BASIC on the next interaction

### 9. Event logging

The bot records useful activity to `telegram_events`, including:

- searches
- media opens
- season selection
- episode source fetches
- bulk selection
- direct link delivery
- upgrade prompts
- admin actions

This gives you a basic analytics trail without needing a separate tracking service.

### 10. Rate limiting

The bot includes in-memory cooldowns per user and action type:

- `search`
- `detail`
- `source`
- `bulk`

This protects the worker API and reduces spam. Since the limiter is in-memory, limits reset if the bot process restarts. For multi-instance scaling, replace this with Redis later.

### 11. Branding for new clients

This codebase is meant to be reused. For each new client, you usually only need to change:

- `BOT_TOKEN`
- `BOT_NAME`
- `BRAND_NAME`
- `SUPPORT_CONTACT`
- `SITE_BASE_URL`
- `WORKER_API_BASE`
- `WORKER_API_KEY`
- `BOT_OWNER_IDS`

Typical branded deployment process:

1. Create a new bot in BotFather
2. Get the bot token
3. Point the bot to the correct worker API
4. Point BASIC redirects to the client website
5. Set owner IDs for the client or your internal team
6. Deploy a new instance with that env file

### 12. Deployment notes

This bot is simple to deploy on a small VPS such as DigitalOcean, Hetzner, or Ubuntu on any cloud provider.

Recommended production setup:

1. Create a server
2. Install Python
3. Copy the project
4. Create `bot/.env`
5. Install dependencies
6. Apply the Supabase schema
7. Run the bot with a process manager

Example process manager options:

- `systemd`
- `pm2`
- `screen` or `tmux` for temporary testing

Example `systemd` service:

```ini
[Unit]
Description=Telegram Movie Download Bot
After=network.target

[Service]
Type=simple
WorkingDirectory=/path/to/repo
ExecStart=/path/to/repo/.venv/bin/python -m bot.main
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### 13. Update workflow

When changing bot behavior:

1. Pull the latest code
2. Update dependencies if needed
3. Review `.env` values
4. Restart the bot process
5. Smoke test `/start`, `/plan`, one movie, and one TV title

## Client / Bot Owner Guide

This section is for the client who owns the branded bot but is not expected to edit Python code.

### What the client receives

The client receives a branded Telegram movie bot that can:

- search movies and TV shows
- redirect BASIC users to a website
- give PRO users direct links
- support manual PRO activation
- track usage in the background

### What the client needs from the developer

To launch a branded copy, the client should provide:

- bot name
- Telegram support username
- website URL
- worker API URL and API key
- Telegram user ID for owner access

Optional:

- logo or brand identity
- pricing plan for PRO access
- terms or support policy

### Daily client usage

The client mostly interacts with the bot as an owner in Telegram.

Common tasks:

1. Check their own bot is online
2. Grant PRO to paid users
3. Revoke access when needed
4. Check a user plan
5. Review basic usage stats

### Client admin commands

Owner commands the client can use:

- `/grant <user_id> <days>`
- `/revoke <user_id>`
- `/user <user_id>`
- `/stats`

### How the client upgrades a user

1. Ask the user to send `/plan`
2. The user copies their Telegram user ID from the bot response
3. The client receives payment off-platform
4. The client opens the bot and runs:

```text
/grant <user_id> <days>
```

5. The user can now receive PRO links inside Telegram

### What the client should tell end users

Suggested explanation:

```text
Send the movie or TV title in the bot.
Tap your result.
If you are on BASIC, the bot sends you to the website.
If you are on PRO, the bot gives you direct links in Telegram.
For series, choose a season, then an episode, or use Select All for the current chunk.
```

### Client limitations to understand

- This v1 bot works in private chats only.
- Bulk links are limited to the current chunk size, default `10`.
- PRO activation is manual in v1.
- If the worker has no sources, the bot cannot create links.
- If the worker is rate limited or unavailable, the bot will show an error.

## End User Commands

Users can run:

- `/start`
- `/help`
- `/plan`
- `/pro`
- `/search <title>`

They can also type the title directly without using `/search`.

## Website Redirect Rules

Current BASIC redirect rules:

- Movies:
  - `/movie/:id?ref=telegram&tier=basic&quality={quality}#download-section`
- TV single episode:
  - `/watch/:id?season={season}&episode={episode}&ref=telegram&tier=basic`

If you change website routes later, you must update the button-building logic in [buttons.py](/c:/Users/LENOVO/OneDrive/Desktop/Emnex/projects/emnexmovie/bot/utils/buttons.py).

## Security Notes

- Keep `SUPABASE_SERVICE_ROLE_KEY` private.
- Keep `WORKER_API_KEY` private.
- Do not commit `bot/.env`.
- The bot does not store media files.
- The bot only returns URLs already resolved by the worker API.
- Rate limiting is enabled, but for larger deployments Redis is recommended later.

## Troubleshooting

### Bot does not start

Check:

- `BOT_TOKEN` is valid
- `bot/.env` exists
- dependencies are installed
- you are running from the repository root with:

```bash
python -m bot.main
```

### `/grant` says owner-only

Check:

- your Telegram numeric user ID is correct
- your ID is listed in `BOT_OWNER_IDS`
- IDs are comma-separated with no invalid characters
- you are using the command in private chat

### BASIC links open the wrong page

Check:

- `SITE_BASE_URL`
- your website routes
- the redirect patterns in [buttons.py](/c:/Users/LENOVO/OneDrive/Desktop/Emnex/projects/emnexmovie/bot/utils/buttons.py)

### PRO links are missing

Check:

- worker API is online
- worker API key is correct
- the selected title actually has processed sources
- the worker is not returning `noSources`

### TV show pages look incomplete

Check:

- the worker detail response includes valid `seasons`
- each season has a usable episode count

### Expired PRO users still look like PRO in the database

The bot resolves this on lookup and interaction. The stored row is corrected back to BASIC when the user is checked again.

## Recommended Next Improvements

Good v2 upgrades for later:

- Redis-based distributed rate limiting and cache
- payment integration for automatic PRO activation
- coupon or referral system
- broadcast messaging for promos
- admin web panel
- analytics dashboard
- webhook mode
- background health checks
- multi-instance deployment support

## Quick Launch Checklist

Use this as the fastest launch sequence:

1. Create the Telegram bot in BotFather
2. Copy `bot/.env.example` to `bot/.env`
3. Fill in all required environment variables
4. Apply [schema.sql](/c:/Users/LENOVO/OneDrive/Desktop/Emnex/projects/emnexmovie/bot/db/schema.sql) to Supabase
5. Install dependencies with `pip install -r bot/requirements.txt`
6. Start the bot with `python -m bot.main`
7. Test `/start`, `/plan`, one movie, and one TV title
8. Add your Telegram user ID to `BOT_OWNER_IDS`
9. Test `/grant <your_user_id> 1`
10. Hand the branded bot to the client

## Summary

This bot gives you:

- a reusable Telegram movie and TV bot
- a BASIC funnel into your website
- a PRO subscription model with direct links
- a manual owner workflow for user upgrades
- Supabase-backed persistence
- a clean base for selling branded deployments to clients
