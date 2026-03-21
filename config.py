import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()

@dataclass
class Config:
    BOT_TOKEN:     str  = field(default_factory=lambda: os.getenv("BOT_TOKEN", ""))
    DATABASE_URL:  str  = field(default_factory=lambda: os.getenv("DATABASE_URL", ""))
    MINI_APP_URL:  str  = field(default_factory=lambda: os.getenv("MINI_APP_URL", ""))
    ADMIN_IDS:     list = field(default_factory=lambda: [
        int(x)
        for x in os.getenv("ADMIN_IDS", "")
                   .strip().strip("[]").replace(" ", "").split(",")
        if x.strip().lstrip("-").isdigit()
    ])
    PAYMENT_CARD:  str  = field(default_factory=lambda: os.getenv("PAYMENT_CARD",  "8600 0000 0000 0000"))
    PAYMENT_OWNER: str  = field(default_factory=lambda: os.getenv("PAYMENT_OWNER", "Karta egasi"))
    SOLUTION_URL:     str  = field(default_factory=lambda: os.getenv("SOLUTION_URL", ""))
    RESULT_GROUP_ID:  str  = field(default_factory=lambda: os.getenv("RESULT_GROUP_ID", ""))

    # ── Rasm saqlash (VPS) ──────────────────────
    IMAGES_DIR:  str = field(default_factory=lambda: os.getenv("IMAGES_DIR",  "/var/www/bot_images"))
    IMAGES_URL:  str = field(default_factory=lambda: os.getenv("IMAGES_URL",  "https://images.eskiz.uz"))

    PRICE_ONCE:        int = 3_500
    PRICE_DAILY:       int = 35_000
    PRICE_MONTHLY:     int = 100_000
    PRICE_RETRY:       int = 3_500   # back-compat
    PRICE_ATTESTATION: int = 10_000  # Attestatsiya — bir martalik
    PRICE_MILLIY:      int = 0        # Milliy sertifikat — oddiy to'lov tizimi (bepul + retry)
    MIN_QUESTIONS:     int = 35
    MAX_QUESTIONS:     int = 50
    ATTESTATION_COUNT: int = 35

    SUBJECTS = {
        'onatili':  '📚 Ona tili',
        'adabiyot': '📖 Adabiyot',
    }

    # ── Ona tili bo'limlari ─────────────────────
    ONA_TILI_BOLIMLAR = {
        'fonetika':      '🔤 Fonetika',
        'imlo':          '✏️ Imlo',
        'morfemika':     '🔩 Morfemika',
        'leksikologiya': '📝 Leksikologiya',
        'morfologiya_m': "📗 Morfologiya (Mustaqil so'zlar)",
        'morfologiya_y': "📘 Morfologiya (Yordamchi so'zlar)",
        'morfologiya_a': "📙 Morfologiya (Alohida so'zlar)",
        'sintaksis':     '📐 Sintaksis',
        'punktuatsiya':  '❗ Punktuatsiya',
        'matnlar':       '📄 Matnlar',
        'uslubiyat':     '🎨 Uslubiyat',
    }

    # Har bir bo'lim uchun sub-mavzular
    ONA_TILI_SUBMAVZULAR = {
        'fonetika':      {
            'tovushlar_tasnifi': "Tovushlar tasnifi",
            'tovush_ozgarishi':  "Tovush o'zgarishlari",
        },
        'imlo':          {
            'togri_yozilgan': "Qaysi so'z to'g'ri yozilgan",
            'imloviy_xato':   "Gapda qaysi turdagi imloviy xato bor",
        },
        'morfemika':     {
            'qoshimchalar': "Qo'shimchalar tasnifi",
            'tub_yasama':   "Tub va yasama so'zlar",
        },
        'leksikologiya': {
            'oz_kochma':     "O'z va ko'chma ma'no",
            'shakl_mano':    "So'zlarning shakl va ma'no-munosabati aralash",
            'omonimlik':     "Omonimlik",
            'paronimlik':    "Paronimlik",
            'ibora':         "Ibora va tasviriy ifodalar",
            'lugatlar':      "Lug'atlardan",
        },
        'morfologiya_m': {
            'ot': "Ot", 'sifat': "Sifat", 'son': "Son",
            'olmosh': "Olmosh", 'ravish': "Ravish", 'fel': "Fe'l",
        },
        'morfologiya_y': {
            'boglovchilar': "Bog'lovchilar",
            'komakchilar':  "Ko'makchilar",
            'yuklamalar':   "Yuklamalar",
        },
        'morfologiya_a': {
            'alohida': "Alohida olingan so'z turkumlari",
        },
        'sintaksis':     {
            'sozlar_boglashi': "So'zlarning bog'lanishi",
            'gap_bolaklari':   "Gap bo'laklari",
            'qoshma_gaplar':   "Qo'shma gaplar",
        },
        'matnlar':       {
            'ilmiy_matn':  "Ilmiy matnlar",
            'badiiy_matn': "Badiiy matnlar",
        },
        'uslubiyat':     {
            'qoshimchalar_uslubiyat': "Qo'shimchalar uslubiyati",
            'sozlar_uslubiyat':       "So'zlar uslubiyati",
        },
        'punktuatsiya':  {},  # sub-mavzu yo'q
    }

    # Moslash uchun — eski kod bilan back-compat
    ONA_TILI_TOPICS = ONA_TILI_BOLIMLAR

    # ── Adabiyot ───────────────────────────────
    ADABIYOT_BOBLAR = {
        '5':  {'1': "1-bob", '2': "2-bob", '3': "3-bob", '4': "4-bob"},
        '6':  {'1': "1-bob", '2': "2-bob", '3': "3-bob", '4': "4-bob"},
        '7':  {'1': "1-bob", '2': "2-bob", '3': "3-bob", '4': "4-bob"},
        '8':  {'1': "1-bob", '2': "2-bob", '3': "3-bob", '4': "4-bob"},
        '9':  {'1': "1-bob", '2': "2-bob", '3': "3-bob", '4': "4-bob"},
        '10': {'1': "1-bob", '2': "2-bob", '3': "3-bob", '4': "4-bob"},
        '11': {
            '1': "1-bob (1-100-betlar)",
            '2': "2-bob (100-198-betlar)",
            '3': "3-bob (1-89-betlar)",
            '4': "4-bob (89-196-betlar)",
        },
    }

    GRADES = {
        '5': '5-sinf', '6': '6-sinf',  '7': '7-sinf',
        '8': '8-sinf', '9': '9-sinf', '10': '10-sinf', '11': '11-sinf',
    }

    DIFFICULTIES = {
        'easy':   '🟢 Oson',
        'medium': "🟡 O'rta",
        'hard':   '🔴 Qiyin',
    }

    def validate(self):
        errors = []
        if not self.BOT_TOKEN:
            errors.append("❌ BOT_TOKEN — .env faylida yo'q!")
        if not self.DATABASE_URL:
            errors.append("❌ DATABASE_URL — .env faylida yo'q!")
        if not self.ADMIN_IDS:
            errors.append("❌ ADMIN_IDS — .env faylida yo'q!")
        if not self.MINI_APP_URL:
            errors.append("⚠️  MINI_APP_URL — .env faylida yo'q (mini app ishlamaydi)")
        if errors:
            for e in errors:
                print(e)
            if any("❌" in e for e in errors):
                raise SystemExit("Bot ishga tushmadi — .env ni to'ldiring!")

config = Config()