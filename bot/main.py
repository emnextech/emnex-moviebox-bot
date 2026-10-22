from __future__ import annotations

import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

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

WEBHOOK_PATH = "/tg/webhook"
PORT = int(os.environ.get("PORT", "8000"))
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "").strip()


def _public_base() -> str | None:
    """Public https base URL of this service (Render injects RENDER_EXTERNAL_URL)."""
    base = (os.environ.get("RENDER_EXTERNAL_URL") or os.environ.get("WEBHOOK_BASE_URL") or "").rstrip("/")
    return base or None


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


def _build() -> tuple[Bot, Dispatcher, ServiceContainer, WorkerApiClient]:
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
        default=DefaultBotProperties(parse_mode=ParseMode.HTML, link_preview_is_disabled=True),
    )
    dp = Dispatcher()
    dp["services"] = services
    for router in (
        start_router,
        discovery_router,
        admin_router,
        search_router,
        discovery_handler_router,
        movie_router,
        tv_router,
        quality_router,
    ):
        dp.include_router(router)
    return bot, dp, services, api_client


def run_webhook(base: str) -> None:
    """Webhook mode: Telegram POSTs updates to us → wakes the instance instantly,
    so there's no polling-offline gap when the free host idles."""
    bot, dp, services, api_client = _build()
    webhook_url = base + WEBHOOK_PATH
    log = logging.getLogger(__name__)

    async def on_startup(_app: web.Application) -> None:
        await set_commands(bot)
        await bot.set_webhook(
            webhook_url,
            secret_token=WEBHOOK_SECRET or None,
            drop_pending_updates=True,
            allowed_updates=dp.resolve_used_update_types(),
        )
        log.info("webhook registered at %s", webhook_url)

    async def on_shutdown(_app: web.Application) -> None:
        try:
            await bot.delete_webhook()
        except Exception:  # pragma: no cover
            pass
        await api_client.close()
        await bot.session.close()

    async def health(_request: web.Request) -> web.Response:
        return web.Response(text="ok")

    app = web.Application()
    app.router.add_get("/", health)
    app.router.add_get("/health", health)
    SimpleRequestHandler(dispatcher=dp, bot=bot, secret_token=WEBHOOK_SECRET or None).register(app, path=WEBHOOK_PATH)
    setup_application(app, dp, bot=bot, services=services)
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)
    log.info("starting webhook server on :%s", PORT)
    web.run_app(app, host="0.0.0.0", port=PORT)


async def run_polling() -> None:
    """Fallback for local dev (no public URL available)."""
    bot, dp, services, api_client = _build()
    try:
        await set_commands(bot)
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot, services=services, allowed_updates=dp.resolve_used_update_types())
    finally:
        await api_client.close()
        await bot.session.close()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    base = _public_base()
    if base:
        run_webhook(base)
    else:
        logging.getLogger(__name__).info("no public URL set — running long-polling (local dev)")
        asyncio.run(run_polling())


if __name__ == "__main__":
    main()
