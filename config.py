BOT_TOKEN = "8618741980:AAG8oJWOx4GWDIaIbP2nGgNEy2sRWdJ2nC8"
ADMIN_IDS = [969814328]
PAYMENT_CARD_NUMBER = "9860350144067617"

import os
from dataclasses import dataclass

@dataclass
class Config:
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "8618741980:AAG8oJWOx4GWDIaIbP2nGgNEy2sRWdJ2nC8")
    ADMIN_IDS: list = None

    # Payment settings
    PAYMENT_AMOUNT: int = 15000  # So'm
    PAYMENT_CARD_NUMBER: str = "9860 3501 4406 7617"
    PAYMENT_CARD_OWNER: str = "Qudrat Iskandarov"

    # Database
    DB_PATH: str = "database/bot.db"

    def __post_init__(self):
        if self.ADMIN_IDS is None:
            # Admin Telegram ID larini shu yerga qo'shing
            self.ADMIN_IDS = [969814328]  # O'z admin ID ingizni kiriting

config = Config()