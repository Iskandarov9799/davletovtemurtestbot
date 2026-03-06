from dotenv import load_dotenv
load_dotenv()

import os
from dataclasses import dataclass

@dataclass
class Config:
    BOT_TOKEN: str = os.getenv("BOT_TOKEN")
    ADMIN_IDS: list = None

    # Payment settings
    PAYMENT_AMOUNT: int = 15000  # So'm
    PAYMENT_CARD_NUMBER: str = "9860 3501 4406 7617"
    PAYMENT_CARD_OWNER: str = "Qudrat Iskandarov"

    # Mini App URL (deploy qilingandan keyin o'zgartiring)
    MINI_APP_URL: str = "https://iskandarov9799.github.io/davletovtemurtestbot/miniapp/"

    # Database
    DB_PATH: str = "database/bot.db"

    def __post_init__(self):
        if self.ADMIN_IDS is None:
            # Admin Telegram ID larini shu yerga qo'shing
            self.ADMIN_IDS = [969814328]  # O'z admin ID ingizni kiriting

config = Config()