from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton,
    WebAppInfo
)
from config import config

# ══════════════════════════════════════════════
# REPLY KEYBOARDS
# ══════════════════════════════════════════════

def phone_keyboard():
    """Ro'yxatdan o'tish — telefon ulashish"""
    return ReplyKeyboardMarkup(
        keyboard=[[
            KeyboardButton(text="📱 Telefon raqamimni ulashish", request_contact=True)
        ]],
        resize_keyboard=True,
        one_time_keyboard=True
    )

def main_menu_keyboard():
    """Asosiy menyu — ro'yxatdan o'tgandan keyin"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📚 Ona tili"),    KeyboardButton(text="📖 Adabiyot")],
            [KeyboardButton(text="🎓 Atestatsiya")],
            [KeyboardButton(text="📊 Natijalarim"), KeyboardButton(text="🏆 Reyting")],
            [KeyboardButton(text="👤 Profil"),       KeyboardButton(text="ℹ️ Yordam")],
        ],
        resize_keyboard=True
    )

def cancel_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Bekor qilish")]],
        resize_keyboard=True,
        one_time_keyboard=True
    )

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
            [KeyboardButton(text="📢 Broadcast"),          KeyboardButton(text="➕ Savol qo'shish")],
            [KeyboardButton(text="📋 Savollar"),           KeyboardButton(text="📥 Excel eksport")],
            [KeyboardButton(text="🔙 Orqaga")],
        ],
        resize_keyboard=True
    )

def skip_image_keyboard():
    """Savol qo'shishda rasm o'tkazib yuborish"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="⏭ Rasmisiz davom etish")],
            [KeyboardButton(text="❌ Bekor qilish")],
        ],
        resize_keyboard=True
    )

# ══════════════════════════════════════════════
# ONA TILI — inline
# ══════════════════════════════════════════════

def onatili_category_keyboard():
    """Ona tili: Mavzulashtirilgan / Aralash / Atestatsiya"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📌 Mavzulashtirilgan", callback_data="onatili:mavzu")],
        [InlineKeyboardButton(text="🎲 Aralash",           callback_data="onatili:aralash")],
        [InlineKeyboardButton(text="🎓 Atestatsiya",       callback_data="onatili:attestation")],
        [InlineKeyboardButton(text="🔙 Orqaga",            callback_data="back:main")],
    ])

def onatili_topics_keyboard():
    """Ona tili mavzulari"""
    buttons = []
    for key, label in config.ONA_TILI_TOPICS.items():
        buttons.append([InlineKeyboardButton(
            text=label, callback_data=f"onatili:topic:{key}"
        )])
    buttons.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data="back:onatili")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# ══════════════════════════════════════════════
# ADABIYOT — inline
# ══════════════════════════════════════════════

def adabiyot_category_keyboard():
    """Adabiyot: Sinflar / Aralash / G'azallar / Atestatsiya"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏫 Sinflar",     callback_data="adabiyot:sinf")],
        [InlineKeyboardButton(text="🎲 Aralash",     callback_data="adabiyot:aralash")],
        [InlineKeyboardButton(text="📜 G'azallar",   callback_data="adabiyot:gazallar")],
        [InlineKeyboardButton(text="🎓 Atestatsiya", callback_data="adabiyot:attestation")],
        [InlineKeyboardButton(text="🔙 Orqaga",      callback_data="back:main")],
    ])

def grades_keyboard():
    """Sinflar: 5-11"""
    buttons = []
    row = []
    for key, label in config.GRADES.items():
        row.append(InlineKeyboardButton(
            text=label, callback_data=f"adabiyot:grade:{key}"
        ))
        if len(row) == 4:  # 4 tadan qator
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data="back:adabiyot")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# ══════════════════════════════════════════════
# QIYINLIK DARAJASI — inline
# ══════════════════════════════════════════════

def difficulty_keyboard(callback_prefix: str):
    """
    callback_prefix — qayerdan chaqirilganiga qarab:
      'onatili:aralash'  → onatili:aralash:easy
      'onatili:topic:fonetika' → onatili:topic:fonetika:easy
      'adabiyot:aralash' → adabiyot:aralash:easy
      'adabiyot:grade:5' → adabiyot:grade:5:easy
      'adabiyot:gazallar'→ adabiyot:gazallar:easy
    """
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🟢 Oson",    callback_data=f"{callback_prefix}:easy"),
            InlineKeyboardButton(text="🟡 O'rta",   callback_data=f"{callback_prefix}:medium"),
            InlineKeyboardButton(text="🔴 Qiyin",   callback_data=f"{callback_prefix}:hard"),
        ],
        [InlineKeyboardButton(text="🔙 Orqaga",     callback_data=f"back:{callback_prefix}")],
    ])

# ══════════════════════════════════════════════
# ATESTATSIYA — inline
# ══════════════════════════════════════════════

def attestation_buy_keyboard(subject: str):
    """Atestatsiya sotib olish"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"💳 Sotib olish — {config.PRICE_ATTESTATION:,} so'm",
            callback_data=f"buy:attestation:{subject}"
        )],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data=f"back:{subject}")],
    ])

def attestation_format_keyboard(subject: str):
    """Atestatsiyani qanday formatda olish: Mini App yoki PDF"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🖥 Mini App",  callback_data=f"attest_fmt:{subject}:miniapp")],
        [InlineKeyboardButton(text="📄 PDF",        callback_data=f"attest_fmt:{subject}:pdf")],
        [InlineKeyboardButton(text="🔙 Orqaga",     callback_data=f"back:{subject}")],
    ])

def miniapp_keyboard(url: str):
    """Mini App ochish tugmasi"""
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🚀 Testni boshlash", web_app=WebAppInfo(url=url))
    ]])

# ══════════════════════════════════════════════
# TO'LOV — inline
# ══════════════════════════════════════════════

def retry_buy_keyboard(access_key: str):
    """Qayta urinish uchun to'lov"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"💳 To'lov — {config.PRICE_RETRY:,} so'm",
            callback_data=f"buy:retry:{access_key}"
        )],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="back:main")],
    ])

def payment_confirm_keyboard(purchase_id: int):
    """Admin: to'lovni tasdiqlash / rad etish"""
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"confirm_pay:{purchase_id}"),
        InlineKeyboardButton(text="❌ Rad etish",  callback_data=f"reject_pay:{purchase_id}"),
    ]])

# ══════════════════════════════════════════════
# ADMIN — savol qo'shish
# ══════════════════════════════════════════════

def subject_keyboard():
    """Fan tanlash (admin uchun)"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📚 Ona tili",  callback_data="addq:subject:onatili")],
        [InlineKeyboardButton(text="📖 Adabiyot",  callback_data="addq:subject:adabiyot")],
        [InlineKeyboardButton(text="❌ Bekor",      callback_data="addq:cancel")],
    ])

def addq_category_keyboard(subject: str):
    """Kategoriya tanlash (admin uchun)"""
    if subject == 'onatili':
        buttons = [
            [InlineKeyboardButton(text="📌 Mavzulashtirilgan", callback_data="addq:cat:mavzu")],
            [InlineKeyboardButton(text="🎲 Aralash",           callback_data="addq:cat:aralash")],
            [InlineKeyboardButton(text="🎓 Atestatsiya",       callback_data="addq:cat:attestation")],
        ]
    else:
        buttons = [
            [InlineKeyboardButton(text="🏫 Sinflar",     callback_data="addq:cat:sinf")],
            [InlineKeyboardButton(text="🎲 Aralash",     callback_data="addq:cat:aralash")],
            [InlineKeyboardButton(text="📜 G'azallar",   callback_data="addq:cat:gazallar")],
            [InlineKeyboardButton(text="🎓 Atestatsiya", callback_data="addq:cat:attestation")],
        ]
    buttons.append([InlineKeyboardButton(text="❌ Bekor", callback_data="addq:cancel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def addq_topic_keyboard():
    """Mavzu tanlash (admin, ona tili mavzu uchun)"""
    buttons = []
    for key, label in config.ONA_TILI_TOPICS.items():
        buttons.append([InlineKeyboardButton(
            text=label, callback_data=f"addq:topic:{key}"
        )])
    buttons.append([InlineKeyboardButton(text="❌ Bekor", callback_data="addq:cancel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def addq_grade_keyboard():
    """Sinf tanlash (admin, adabiyot sinf uchun)"""
    buttons = []
    row = []
    for key, label in config.GRADES.items():
        row.append(InlineKeyboardButton(
            text=label, callback_data=f"addq:grade:{key}"
        ))
        if len(row) == 4:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton(text="❌ Bekor", callback_data="addq:cancel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def addq_difficulty_keyboard():
    """Qiyinlik tanlash (admin uchun)"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🟢 Oson",  callback_data="addq:diff:easy"),
            InlineKeyboardButton(text="🟡 O'rta", callback_data="addq:diff:medium"),
            InlineKeyboardButton(text="🔴 Qiyin", callback_data="addq:diff:hard"),
        ],
        [InlineKeyboardButton(text="❌ Bekor", callback_data="addq:cancel")],
    ])

def correct_answer_keyboard():
    """To'g'ri javob tanlash (admin uchun)"""
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="A", callback_data="addq:correct:A"),
        InlineKeyboardButton(text="B", callback_data="addq:correct:B"),
        InlineKeyboardButton(text="C", callback_data="addq:correct:C"),
        InlineKeyboardButton(text="D", callback_data="addq:correct:D"),
    ]])