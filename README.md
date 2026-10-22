# EmnexMovies Telegram Bot

aiogram long-polling bot for EmnexMovies. Deployed on Render (Docker). A tiny HTTP
health server runs on `$PORT` so the platform health check passes while the bot polls.
A scheduled GitHub Action pings the service to keep Render's free instance awake.

Env vars (set in Render, never committed): `BOT_TOKEN`, `WORKER_API_BASE`,
`MINIAPP_URL`, `SITE_BASE_URL`, `BOT_OWNER_IDS`, and optionally `SUPABASE_URL` /
`SUPABASE_SERVICE_ROLE_KEY` (omit = in-memory user store).
