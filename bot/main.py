from __future__ import annotations

import asyncio
import logging
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer


def _start_health_server() -> None:
    """Tiny HTTP server so Koyeb/Render health checks pass (the bot itself polls)."""
    port = int(os.environ.get("PORT", "8000"))

    class _Health(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            self.send_response(200)
            self.send_header("content-type", "text/plain")
            self.end_headers()
            self.wfile.write(b"ok")

        def log_message(self, *args) -> None:  # silence request logging
            return

    try:
        server = HTTPServer(("0.0.0.0", port), _Health)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        logging.getLogger(__name__).info("health server listening on :%s", port)
    except OSError as exc:  # pragma: no cover - port already taken is non-fatal
        logging.getLogger(__name__).warning("health server not started: %s", exc)

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand

from bot.commands.admin import router as admin_router
from bot.commands.discovery import router as discovery_router
from bot.commands.search import router as search_router
from bot.commands.start import router as start_router
from bot.config.settings import get_settings
from bot.handlers.discovery_handler import router as discovery_handler_router
from bot.handlers.movie_handler import router as movie_router
from bot.handlers.quality_handler import router as quality_router
from bot.handlers.tv_handler import router as tv_router
from bot.runtime import ServiceContainer
from bot.services import RateLimiter, SessionStore, UserService, WorkerApiClient


async def set_commands(bot: Bot) -> None:
    await bot.set_my_commands(
        [
            BotCommand(command="start", description="Start the bot"),
            BotCommand(command="help", description="How to use the bot"),
            BotCommand(command="plan", description="Check your current plan"),
            BotCommand(command="pro", description="See PRO benefits"),
            BotCommand(command="search", description="Search for a title"),
            BotCommand(command="discover", description="Open curated sections"),
            BotCommand(command="browse", description="Browse by filters"),
        ]
    )


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    _start_health_server()

    settings = get_settings()
    api_client = WorkerApiClient(settings)
    user_service = UserService(settings)
    rate_limiter = RateLimiter(settings)
    session_store = SessionStore()
    services = ServiceContainer(
        settings=settings,
        api_client=api_client,
        user_service=user_service,
        rate_limiter=rate_limiter,
        session_store=session_store,
    )

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(
            parse_mode=ParseMode.HTML,
            link_preview_is_disabled=True,
        ),
    )
    dp = Dispatcher()
    dp["services"] = services
    dp.include_router(start_router)
    dp.include_router(discovery_router)
    dp.include_router(admin_router)
    dp.include_router(search_router)
    dp.include_router(discovery_handler_router)
    dp.include_router(movie_router)
    dp.include_router(tv_router)
    dp.include_router(quality_router)

    try:
        await set_commands(bot)
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot, services=services, allowed_updates=dp.resolve_used_update_types())
    finally:
        await api_client.close()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
