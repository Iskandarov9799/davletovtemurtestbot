from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton,
    WebAppInfo
)
from config import config

def phone_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Telefon raqamimni ulashish", request_contact=True)]],
        resize_keyboard=True, one_time_keyboard=True
    )

def main_menu_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📚 Ona tili"),        KeyboardButton(text="📖 Adabiyot")],
            [KeyboardButton(text="🎓 Atestatsiya")],
            [KeyboardButton(text="🎬 Videodarslar"),     KeyboardButton(text="🎧 Audiolar")],
            [KeyboardButton(text="🏅 Milliy sertifikat")],
            [KeyboardButton(text="📊 Natijalarim"),      KeyboardButton(text="🏆 Reyting")],
            [KeyboardButton(text="👤 Profil"),            KeyboardButton(text="ℹ️ Yordam")],
        ],
        resize_keyboard=True
    )

def cancel_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="payment:cancel")]
    ])

def back_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🔙 Orqaga")]],
        resize_keyboard=True
    )

def admin_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="💰 Kutayotgan to'lovlar")],
            [KeyboardButton(text="👥 Foydalanuvchilar"),  KeyboardButton(text="📊 Statistika")],
            [KeyboardButton(text="👥 A'zolar"),            KeyboardButton(text="📢 Broadcast")],
            [KeyboardButton(text="➕ Savol qo'shish"),     KeyboardButton(text="📋 Savollar")],
            [KeyboardButton(text="📥 Excel eksport"),      KeyboardButton(text="📤 Excel import")],
            [KeyboardButton(text="🗂 Bo'lim o'chirish"),   KeyboardButton(text="➕ Bo'lim qo'shish")],
            [KeyboardButton(text="🗑 Savollarni o'chirish"),   KeyboardButton(text="🔗 Yechim linki")],
            [KeyboardButton(text="🔙 Orqaga")],
        ],
        resize_keyboard=True
    )

def skip_image_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="⏭ Rasmisiz davom etish")],
            [KeyboardButton(text="❌ Bekor qilish")],
        ],
        resize_keyboard=True
    )

# ══════════════════════════════════════════════
# ONA TILI
# ══════════════════════════════════════════════

def onatili_category_keyboard():
    """Atestatsiya YO'Q — asosiy menyuda alohida turibdi"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📌 Mavzulashtirilgan",  callback_data="onatili:mavzu")],
        [InlineKeyboardButton(text="🔀 Mavzulardan aralash", callback_data="onatili:aralash")],
    ])

def onatili_bolimlar_keyboard():
    buttons = []
    for key, label in config.ONA_TILI_BOLIMLAR.items():
        buttons.append([InlineKeyboardButton(text=label, callback_data=f"onatili:bolim:{key}")])
    buttons.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data="back:onatili")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def onatili_submavzu_keyboard(bolim: str):
    submavzular = config.ONA_TILI_SUBMAVZULAR.get(bolim, {})
    buttons = []
    for key, label in submavzular.items():
        buttons.append([InlineKeyboardButton(
            text=label, callback_data=f"onatili:sub:{bolim}:{key}"
        )])
    buttons.append([InlineKeyboardButton(
        text="🔀 Aralash (barcha savollar)", callback_data=f"onatili:sub:{bolim}:__aralash__"
    )])
    buttons.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data="back:onatili:bolimlar")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def onatili_topics_keyboard():
    return onatili_bolimlar_keyboard()

# ══════════════════════════════════════════════
# ADABIYOT
# ══════════════════════════════════════════════

def adabiyot_category_keyboard():
    """Atestatsiya YO'Q — asosiy menyuda alohida turibdi"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏫 Sinflar bo'yicha",  callback_data="adabiyot:sinf")],
        [InlineKeyboardButton(text="🔀 Aralash",           callback_data="adabiyot:aralash")],
        [InlineKeyboardButton(text="📜 G'azallar",         callback_data="adabiyot:gazallar")],
        [InlineKeyboardButton(text="🎭 She'riy san'atlar", callback_data="adabiyot:sheriy")],
        [InlineKeyboardButton(text="📖 Badiiy parchalar",  callback_data="adabiyot:badiiy")],
        [InlineKeyboardButton(text="🔙 Orqaga",            callback_data="back:main")],
    ])

def grades_keyboard():
    buttons = []
    row = []
    for key, label in config.GRADES.items():
        row.append(InlineKeyboardButton(text=label, callback_data=f"adabiyot:grade:{key}"))
        if len(row) == 4:
            buttons.append(row); row = []
    if row: buttons.append(row)
    buttons.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data="back:adabiyot")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def adabiyot_boblar_keyboard(grade: str):
    boblar = config.ADABIYOT_BOBLAR.get(grade, {})
    buttons = []
    for key, label in boblar.items():
        buttons.append([InlineKeyboardButton(
            text=label, callback_data=f"adabiyot:bob:{grade}:{key}"
        )])
    buttons.append([InlineKeyboardButton(
        text="🔀 Barcha boblar (aralash)", callback_data=f"adabiyot:grade_aralash:{grade}"
    )])
    buttons.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data="back:adabiyot:sinflar")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# ══════════════════════════════════════════════
# ATESTATSIYA
# ══════════════════════════════════════════════

def attestation_buy_standalone_keyboard():
    from config import config
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"💳 Sotib olish — {config.PRICE_ATTESTATION:,} so'm",
            callback_data="buy:attestation"
        )],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="back:main")],
    ])

def milliy_buy_keyboard():
    from config import config
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"💳 Sotib olish — {config.PRICE_ATTESTATION:,} so'm",
            callback_data="buy:milliy"
        )],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="back:main")],
    ])

def attestation_buy_keyboard(subject: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"💳 Sotib olish — {config.PRICE_ATTESTATION:,} so'm",
            callback_data=f"buy:attestation:{subject}"
        )],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="back:attestation")],
    ])

def attestation_format_keyboard(subject: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🖥 Mini App", callback_data=f"attest_fmt:{subject}:miniapp")],
        [InlineKeyboardButton(text="📄 PDF",       callback_data=f"attest_fmt:{subject}:pdf")],
        [InlineKeyboardButton(text="🔙 Orqaga",    callback_data="back:attestation")],
    ])

# ══════════════════════════════════════════════
# TO'LOV
# ══════════════════════════════════════════════

def payment_options_keyboard(access_key: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="1️⃣ Bir martalik — 3,500 so'm",
            callback_data=f"pay:once:{access_key}"
        )],
        [InlineKeyboardButton(
            text="📅 Kunlik — 35,000 so'm",
            callback_data=f"pay:daily:{access_key}"
        )],
        [InlineKeyboardButton(
            text="📆 Oylik — 100,000 so'm",
            callback_data=f"pay:monthly:{access_key}"
        )],
        [InlineKeyboardButton(text="❌ Bekor", callback_data="payment:cancel")],
    ])

def retry_buy_keyboard(access_key: str):
    return payment_options_keyboard(access_key)

def payment_confirm_keyboard(purchase_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"confirm_pay:{purchase_id}"),
        InlineKeyboardButton(text="❌ Rad etish",  callback_data=f"reject_pay:{purchase_id}"),
    ]])

def miniapp_keyboard(url: str):
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🚀 Testni boshlash", web_app=WebAppInfo(url=url))
    ]])

# ══════════════════════════════════════════════
# ADMIN — savol qo'shish
# ══════════════════════════════════════════════

def subject_keyboard():
    """Fan tanlash — admin savol qo'shganda"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📚 Ona tili",          callback_data="addq:subject:onatili")],
        [InlineKeyboardButton(text="📖 Adabiyot",          callback_data="addq:subject:adabiyot")],
        [InlineKeyboardButton(text="🎓 Attestatsiya",      callback_data="addq:subject:attestation")],
        [InlineKeyboardButton(text="🏅 Milliy sertifikat", callback_data="addq:subject:milliy")],
        [InlineKeyboardButton(text="❌ Bekor",              callback_data="addq:cancel")],
    ])

def addq_category_keyboard(subject: str):
    """Kategoriya tanlash — fanga qarab"""
    if subject == 'onatili':
        buttons = [
            [InlineKeyboardButton(text="📌 Mavzulashtirilgan", callback_data="addq:cat:mavzu")],
            [InlineKeyboardButton(text="🔀 Aralash",           callback_data="addq:cat:aralash")],
        ]
    elif subject == 'adabiyot':
        buttons = [
            [InlineKeyboardButton(text="🏫 Sinflar",           callback_data="addq:cat:sinf")],
            [InlineKeyboardButton(text="🔀 Aralash",           callback_data="addq:cat:aralash")],
            [InlineKeyboardButton(text="📜 G'azallar",         callback_data="addq:cat:gazallar")],
            [InlineKeyboardButton(text="🎭 She'riy san'atlar", callback_data="addq:cat:sheriy")],
            [InlineKeyboardButton(text="📖 Badiiy parchalar",  callback_data="addq:cat:badiiy")],
        ]
    elif subject == 'attestation':
        # Attestatsiya — to'g'ridan savol turi tanlash
        buttons = [
            [InlineKeyboardButton(text="🔘 Variantli (A/B/C/D)",  callback_data="addq:qtype:choice")],
        ]
    elif subject == 'milliy':
        # Milliy sertifikat — variantli yoki yozma
        buttons = [
            [InlineKeyboardButton(text="🔘 Variantli (1-35)",      callback_data="addq:qtype:choice")],
            [InlineKeyboardButton(text="✏️ Yozma 1 qism (36-38)", callback_data="addq:qtype:written1")],
            [InlineKeyboardButton(text="✏️ Yozma 2 qism (39-44)", callback_data="addq:qtype:written2")],
        ]
    else:
        buttons = []
    buttons.append([InlineKeyboardButton(text="❌ Bekor", callback_data="addq:cancel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def addq_topic_keyboard():
    buttons = []
    for key, label in config.ONA_TILI_BOLIMLAR.items():
        buttons.append([InlineKeyboardButton(text=label, callback_data=f"addq:topic:{key}")])
    buttons.append([InlineKeyboardButton(text="❌ Bekor", callback_data="addq:cancel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def addq_submavzu_keyboard(bolim: str):
    submavzular = config.ONA_TILI_SUBMAVZULAR.get(bolim, {})
    buttons = []
    for key, label in submavzular.items():
        buttons.append([InlineKeyboardButton(text=label, callback_data=f"addq:sub:{key}")])
    buttons.append([InlineKeyboardButton(text="❌ Bekor", callback_data="addq:cancel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def addq_grade_keyboard():
    buttons = []
    row = []
    for key, label in config.GRADES.items():
        row.append(InlineKeyboardButton(text=label, callback_data=f"addq:grade:{key}"))
        if len(row) == 4:
            buttons.append(row); row = []
    if row: buttons.append(row)
    buttons.append([InlineKeyboardButton(text="❌ Bekor", callback_data="addq:cancel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def addq_bob_keyboard(grade: str):
    boblar = config.ADABIYOT_BOBLAR.get(grade, {})
    buttons = []
    for key, label in boblar.items():
        buttons.append([InlineKeyboardButton(text=label, callback_data=f"addq:bob:{key}")])
    buttons.append([InlineKeyboardButton(text="❌ Bekor", callback_data="addq:cancel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def addq_difficulty_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🟢 Oson",  callback_data="addq:diff:easy"),
            InlineKeyboardButton(text="🟡 O'rta", callback_data="addq:diff:medium"),
            InlineKeyboardButton(text="🔴 Qiyin", callback_data="addq:diff:hard"),
        ],
        [InlineKeyboardButton(text="❌ Bekor", callback_data="addq:cancel")],
    ])

def correct_answer_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="A", callback_data="addq:correct:A"),
        InlineKeyboardButton(text="B", callback_data="addq:correct:B"),
        InlineKeyboardButton(text="C", callback_data="addq:correct:C"),
        InlineKeyboardButton(text="D", callback_data="addq:correct:D"),
    ]])