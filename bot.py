import asyncio
import logging
import json
from aiohttp import web
from aiogram import Bot, Dispatcher, BaseMiddleware
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import TelegramObject, Message, CallbackQuery
from typing import Callable, Awaitable, Any, Dict
from config import config


class PrivateChatMiddleware(BaseMiddleware):
    """Faqat private chat da ishlaydi. Guruh/kanal va ban xabarlarini o'tkazib yuboradi."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        if isinstance(event, Message):
            if event.web_app_data:
                return await handler(event, data)
            if event.chat.type != "private":
                return
            from database.db import is_banned
            if await is_banned(event.from_user.id):
                await event.answer("🚫 Siz botdan bloklangansiz. Admin bilan bog'laning.")
                return
        elif isinstance(event, CallbackQuery):
            if event.message and event.message.chat.type != "private":
                return
            from database.db import is_banned
            if await is_banned(event.from_user.id):
                await event.answer("🚫 Bloklangansiz.", show_alert=True)
                return
        return await handler(event, data)


logging.basicConfig(
    level  = logging.INFO,
    format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════
# API SERVER — Mini App uchun savollarni beradi
# ══════════════════════════════════════════════

async def api_questions(request: web.Request) -> web.Response:
    """GET /api/bolim/{bolim_num}?token=SECRET"""

    # Token tekshirish
    token = request.rel_url.query.get('token', '')
    if token != config.API_SECRET:
        return web.Response(
            status=403,
            content_type='application/json',
            text=json.dumps({"error": "Forbidden"})
        )

    bolim_num = request.match_info.get('bolim_num', '')
    if not bolim_num.isdigit() or not (1 <= int(bolim_num) <= 10):
        return web.Response(
            status=400,
            content_type='application/json',
            text=json.dumps({"error": "bolim_num 1-10 orasida bo'lishi kerak"})
        )

    bolim_num = int(bolim_num)

    from database.db import get_questions
    from handlers.test_handler import questions_to_miniapp

    questions = await get_questions(
        subject='attestation',
        category='attestation',
        subcategory=f'bolim_{bolim_num}',
        is_attestation=True,
        count=config.ATTESTATION_COUNT
    )

    payload = {
        "meta": {
            "subject":        "attestation",
            "category":       "attestation",
            "subcategory":    f"bolim_{bolim_num}",
            "is_attestation": True,
            "solution_url":   config.SOLUTION_URL,
        },
        "questions": questions_to_miniapp(questions)
    }

    return web.Response(
        status=200,
        content_type='application/json',
        headers={
            'Access-Control-Allow-Origin': '*',
            'Cache-Control': 'no-cache',
        },
        text=json.dumps(payload, ensure_ascii=False)
    )


async def api_health(request: web.Request) -> web.Response:
    """GET /health — server ishlayaptimi?"""
    return web.Response(
        content_type='application/json',
        text=json.dumps({"status": "ok"})
    )


async def start_api_server():
    """aiohttp web serverini ishga tushirish."""
    app = web.Application()
    app.router.add_get('/api/bolim/{bolim_num}', api_questions)
    app.router.add_get('/health', api_health)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', config.API_PORT)
    await site.start()
    logger.info(f"🌐 API server ishga tushdi: http://0.0.0.0:{config.API_PORT}")
    return runner


async def main():
    config.validate()

    from database.connection import init_engine, init_db
    init_engine()
    await init_db()

    # API serverni ishga tushirish
    api_runner = await start_api_server()

    bot = Bot(
        token   = config.BOT_TOKEN,
        default = DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher(storage=MemoryStorage())

    dp.message.middleware(PrivateChatMiddleware())
    dp.callback_query.middleware(PrivateChatMiddleware())

    from handlers import registration, payment, test_handler, admin, question_editor
    from handlers import miniapp_handler

    dp.include_router(admin.router)
    dp.include_router(miniapp_handler.router)
    dp.include_router(registration.router)
    dp.include_router(payment.router)
    dp.include_router(test_handler.router)
    dp.include_router(question_editor.router)

    logger.info("🚀 Bot ishga tushdi! Admin IDs: %s", config.ADMIN_IDS)

    try:
        await dp.start_polling(
            bot,
            allowed_updates=[
                "message",
                "callback_query",
                "inline_query",
                "chosen_inline_result",
                "web_app_data",
            ]
        )
    except KeyboardInterrupt:
        pass
    finally:
        await bot.session.close()
        await api_runner.cleanup()
        logger.info("🛑 Bot to'xtatildi.")


if __name__ == "__main__":
    asyncio.run(main())