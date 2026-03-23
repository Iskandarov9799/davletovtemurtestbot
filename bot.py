import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from config import config

logging.basicConfig(
    level  = logging.INFO,
    format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


async def main():
    config.validate()

    from database.connection import init_engine, init_db
    init_engine()
    await init_db()

    # Keep-alive (Render uchun, agar ishlatilsa)
    # from keep_alive import start_web_server
    # await start_web_server()

    bot = Bot(
        token   = config.BOT_TOKEN,
        default = DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher(storage=MemoryStorage())

    # ── Routerlar ────────────────────────────────
    from handlers import registration, payment, test_handler, admin, question_editor
    from handlers import web_app_handler   # ← YANGI: tg.sendData handler

    dp.include_router(admin.router)
    dp.include_router(web_app_handler.router)  # ← ENG MUHIM: birinchilardan bo'lishi kerak
    dp.include_router(registration.router)
    dp.include_router(payment.router)
    dp.include_router(test_handler.router)
    dp.include_router(question_editor.router)

    logger.info("🚀 Bot ishga tushdi! Admin IDs: %s", config.ADMIN_IDS)

    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    except KeyboardInterrupt:
        pass
    finally:
        await bot.session.close()
        logger.info("🛑 Bot to'xtatildi.")


if __name__ == "__main__":
    asyncio.run(main())