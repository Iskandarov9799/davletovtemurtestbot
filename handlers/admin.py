from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command

from database.db import get_all_users, get_pending_payments
from keyboards.keyboards import admin_keyboard, main_menu_keyboard
from config import config

router = Router()

def admin_only(func):
    """Admin decorator"""
    async def wrapper(message: Message, *args, **kwargs):
        if message.from_user.id not in config.ADMIN_IDS:
            await message.answer("⛔ Siz admin emassiz!")
            return
        return await func(message, *args, **kwargs)
    return wrapper

@router.message(F.text == "👥 Barcha foydalanuvchilar")
async def all_users(message: Message):
    """Barcha foydalanuvchilar ro'yxati"""
    if message.from_user.id not in config.ADMIN_IDS:
        return

    users = get_all_users()

    total = len(users)
    registered = sum(1 for u in users if u['is_registered'])
    paid = sum(1 for u in users if u['payment_confirmed'])

    text = (
        f"👥 <b>Foydalanuvchilar statistikasi:</b>\n\n"
        f"📊 Jami: <b>{total}</b>\n"
        f"✅ Ro'yxatdan o'tgan: <b>{registered}</b>\n"
        f"💰 To'lov qilgan: <b>{paid}</b>\n\n"
        f"<b>So'nggi 10 ta:</b>\n"
    )

    for u in users[:10]:
        status = "💰" if u['payment_confirmed'] else ("⏳" if u['is_paid'] else "👤")
        text += f"{status} {u['full_name']} | {u['phone_number'] or 'raqam yo\'q'}\n"

    await message.answer(text, parse_mode="HTML")

@router.message(F.text == "📊 Statistika")
async def statistics(message: Message):
    """Bot statistikasi"""
    if message.from_user.id not in config.ADMIN_IDS:
        return

    users = get_all_users()
    pending = get_pending_payments()

    total = len(users)
    registered = sum(1 for u in users if u['is_registered'])
    paid_confirmed = sum(1 for u in users if u['payment_confirmed'])
    paid_pending = len(pending)
    income = paid_confirmed * config.PAYMENT_AMOUNT

    await message.answer(
        f"📊 <b>Bot Statistikasi</b>\n\n"
        f"👥 Jami foydalanuvchilar: <b>{total}</b>\n"
        f"✅ Ro'yxatdan o'tgan: <b>{registered}</b>\n"
        f"💰 To'lov tasdiqlangan: <b>{paid_confirmed}</b>\n"
        f"⏳ Kutayotgan to'lov: <b>{paid_pending}</b>\n\n"
        f"💵 Jami daromad: <b>{income:,} so'm</b>",
        parse_mode="HTML"
    )

@router.message(F.text == "🔙 Orqaga")
async def back_to_user(message: Message):
    """Orqaga qaytish"""
    from database.db import is_user_paid
    paid = is_user_paid(message.from_user.id)
    await message.answer(
        "🔙 Asosiy menyuga qaytdingiz.",
        reply_markup=main_menu_keyboard(is_paid=paid)
    )