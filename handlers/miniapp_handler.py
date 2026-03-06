import json
from aiogram import Router, F, Bot
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

from database.db import is_user_paid, is_user_registered, save_test_result
from keyboards.keyboards import main_menu_keyboard
from config import config

router = Router()

def miniapp_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="🚀 Testni boshlash",
            web_app=WebAppInfo(url=config.MINI_APP_URL)
        )
    ]])

@router.message(F.text == "📝 Testni boshlash")
async def open_miniapp(message: Message):
    if not is_user_registered(message.from_user.id):
        await message.answer("❌ Avval ro'yxatdan o'ting! /start")
        return
    if not is_user_paid(message.from_user.id):
        await message.answer(
            "❌ Test uchun to'lov qilishingiz kerak!\n💳 /pay buyrug'ini yuboring.",
            reply_markup=main_menu_keyboard(is_paid=False)
        )
        return
    await message.answer(
        "📚 <b>Ona tili va Adabiyot Testi</b>\n\n"
        "🎯 Qiyinlik darajasini o'zingiz tanlaysiz\n"
        "📊 30 ta random savol\n"
        "✅ Har savolda to'g'ri javob ko'rsatiladi\n"
        "⏭ Savolni o'tkazib yuborish mumkin\n\n"
        "Pastdagi tugmani bosib testni boshlang:",
        reply_markup=miniapp_keyboard(),
        parse_mode="HTML"
    )

@router.message(F.web_app_data)
async def receive_miniapp_data(message: Message, bot: Bot):
    """Mini App dan natija qabul qilish"""
    try:
        data = json.loads(message.web_app_data.data)
        correct = data.get('correct', 0)
        wrong = data.get('wrong', 0)
        skip = data.get('skip', 0)
        total = data.get('total', 30)
        pct = data.get('score', 0)

        # DB ga saqlash
        from datetime import datetime
        save_test_result(
            telegram_id=message.from_user.id,
            correct=correct,
            wrong=wrong,
            started_at=datetime.now().isoformat(),
            difficulty="mixed"
        )

        # Baho
        if pct >= 90: grade, emoji = "A'lo (5)", "🏆"
        elif pct >= 70: grade, emoji = "Yaxshi (4)", "🎉"
        elif pct >= 50: grade, emoji = "Qoniqarli (3)", "📚"
        else: grade, emoji = "Qoniqarsiz (2)", "😔"

        await message.answer(
            f"{emoji} <b>Test natijasi saqlandi!</b>\n\n"
            f"━━━━━━━━━━━━━\n"
            f"✅ To'g'ri: <b>{correct}/{total}</b>\n"
            f"❌ Xato: <b>{wrong}/{total}</b>\n"
            f"⏭ O'tkazildi: <b>{skip}</b>\n"
            f"📈 Ball: <b>{pct}%</b>\n"
            f"🎓 Baho: <b>{grade}</b>\n"
            f"━━━━━━━━━━━━━",
            reply_markup=main_menu_keyboard(is_paid=True),
            parse_mode="HTML"
        )

        # Adminlarga xabar
        for admin_id in config.ADMIN_IDS:
            try:
                await bot.send_message(
                    chat_id=admin_id,
                    text=(
                        f"📊 Yangi test natijasi\n"
                        f"👤 {message.from_user.full_name}\n"
                        f"📈 {pct}% ({correct}/{total})"
                    )
                )
            except Exception:
                pass

    except Exception as e:
        await message.answer(f"❌ Natijani saqlashda xato: {e}")