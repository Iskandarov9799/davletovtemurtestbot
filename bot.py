import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import config
from database.db import init_db
from database.questions_data import seed_questions
from handlers import registration, payment, test_handler, admin
from keep_alive import start_web_server

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

async def main():
    logger.info("🚀 Bot ishga tushmoqda...")

    init_db()
    seed_questions()

    # Render uchun web server parallel ishlatiladi
    await start_web_server()

    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )

    dp = Dispatcher(storage=MemoryStorage())

    dp.include_router(registration.router)
    dp.include_router(payment.router)
    dp.include_router(test_handler.router)
    dp.include_router(admin.router)

    logger.info("✅ Bot muvaffaqiyatli ishga tushdi!")

    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())