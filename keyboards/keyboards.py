from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)

# ============ REPLY KEYBOARDS ============

def phone_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Telefon raqamimni ulashish", request_contact=True)]],
        resize_keyboard=True, one_time_keyboard=True
    )

def main_menu_keyboard(is_paid=False):
    buttons = []
    if is_paid:
        buttons.append([KeyboardButton(text="📝 Testni boshlash")])
        buttons.append([KeyboardButton(text="📊 Mening natijalarim"), KeyboardButton(text="🏆 Reyting")])
    else:
        buttons.append([KeyboardButton(text="💳 To'lov qilish")])
    buttons.append([KeyboardButton(text="ℹ️ Ma'lumot")])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

def cancel_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Bekor qilish")]],
        resize_keyboard=True, one_time_keyboard=True
    )

def admin_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="💰 Kutayotgan to'lovlar")],
            [KeyboardButton(text="👥 Foydalanuvchilar"), KeyboardButton(text="📊 Statistika")],
            [KeyboardButton(text="📢 Broadcast"), KeyboardButton(text="➕ Savol qo'shish")],
            [KeyboardButton(text="📋 Savollar"), KeyboardButton(text="📥 Excel eksport")],
            [KeyboardButton(text="🔙 Orqaga")]
        ],
        resize_keyboard=True
    )

def skip_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="⏭ Rasmisiz davom etish")],
                  [KeyboardButton(text="❌ Bekor qilish")]],
        resize_keyboard=True
    )

# ============ INLINE KEYBOARDS ============

def difficulty_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🟢 Oson", callback_data="diff:easy"),
            InlineKeyboardButton(text="🟡 O'rta", callback_data="diff:medium"),
            InlineKeyboardButton(text="🔴 Qiyin", callback_data="diff:hard"),
        ],
        [InlineKeyboardButton(text="🎲 Aralash", callback_data="diff:mixed")]
    ])

def payment_confirm_keyboard(telegram_id):
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"confirm_pay:{telegram_id}"),
        InlineKeyboardButton(text="❌ Rad etish", callback_data=f"reject_pay:{telegram_id}")
    ]])

def test_answer_keyboard(q_index):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🅰 A", callback_data=f"answer:{q_index}:A"),
            InlineKeyboardButton(text="🅱 B", callback_data=f"answer:{q_index}:B"),
        ],
        [
            InlineKeyboardButton(text="🅲 C", callback_data=f"answer:{q_index}:C"),
            InlineKeyboardButton(text="🅳 D", callback_data=f"answer:{q_index}:D"),
        ]
    ])

def start_test_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Testni boshlash!", callback_data="start_test")]
    ])

def correct_answer_keyboard(q_index):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="A", callback_data=f"setcorrect:{q_index}:A"),
         InlineKeyboardButton(text="B", callback_data=f"setcorrect:{q_index}:B"),
         InlineKeyboardButton(text="C", callback_data=f"setcorrect:{q_index}:C"),
         InlineKeyboardButton(text="D", callback_data=f"setcorrect:{q_index}:D")]
    ])