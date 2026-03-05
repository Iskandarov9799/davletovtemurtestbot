from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)

# ============ REPLY KEYBOARDS ============

def phone_keyboard():
    """Telefon raqamini ulashish tugmasi"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📱 Telefon raqamimni ulashish", request_contact=True)]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )

def main_menu_keyboard(is_paid: bool = False):
    """Asosiy menyu"""
    buttons = []

    if is_paid:
        buttons.append([KeyboardButton(text="📝 Testni boshlash")])
        buttons.append([KeyboardButton(text="📊 Mening natijalarim")])
    else:
        buttons.append([KeyboardButton(text="💳 To'lov qilish")])

    buttons.append([KeyboardButton(text="ℹ️ Ma'lumot")])

    return ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True
    )

def cancel_keyboard():
    """Bekor qilish tugmasi"""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Bekor qilish")]],
        resize_keyboard=True,
        one_time_keyboard=True
    )

def admin_keyboard():
    """Admin panel klaviaturasi"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="💰 Kutayotgan to'lovlar")],
            [KeyboardButton(text="👥 Barcha foydalanuvchilar")],
            [KeyboardButton(text="📊 Statistika")],
            [KeyboardButton(text="🔙 Orqaga")]
        ],
        resize_keyboard=True
    )

# ============ INLINE KEYBOARDS ============

def payment_confirm_keyboard(telegram_id: int):
    """Admin uchun to'lovni tasdiqlash/rad etish"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Tasdiqlash",
                    callback_data=f"confirm_pay:{telegram_id}"
                ),
                InlineKeyboardButton(
                    text="❌ Rad etish",
                    callback_data=f"reject_pay:{telegram_id}"
                )
            ]
        ]
    )

def test_answer_keyboard(question_index: int):
    """Test javob variantlari"""
    options = [
        ("A", f"answer:{question_index}:A"),
        ("B", f"answer:{question_index}:B"),
        ("C", f"answer:{question_index}:C"),
        ("D", f"answer:{question_index}:D"),
    ]
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🅰 A", callback_data=options[0][1]),
                InlineKeyboardButton(text="🅱 B", callback_data=options[1][1]),
            ],
            [
                InlineKeyboardButton(text="🅲 C", callback_data=options[2][1]),
                InlineKeyboardButton(text="🅳 D", callback_data=options[3][1]),
            ]
        ]
    )

def start_test_keyboard():
    """Test boshlash tugmasi"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🚀 Testni boshlash!", callback_data="start_test")]
        ]
    )