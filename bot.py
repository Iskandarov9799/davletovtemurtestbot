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

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

async def main():
    logger.info("🚀 Bot ishga tushmoqda...")

    # Init database
    init_db()
    seed_questions()

    # Create bot
    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )

    # Create dispatcher with FSM storage
    dp = Dispatcher(storage=MemoryStorage())

    # Register routers (tartib muhim!)
    dp.include_router(registration.router)
    dp.include_router(payment.router)
    dp.include_router(test_handler.router)
    dp.include_router(admin.router)

    logger.info("✅ Bot muvaffaqiyatli ishga tushdi!")

    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()
        logger.info("🛑 Bot to'xtatildi.")

if __name__ == "__main__":
    asyncio.run(main())