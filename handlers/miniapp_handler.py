import json
import base64
import zlib
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.fsm.context import FSMContext

from database.db import (
    is_user_paid, is_user_registered,
    save_test_result, get_random_questions
)
from keyboards.keyboards import main_menu_keyboard
from config import config

router = Router()

DIFFICULTY_NAMES = {
    'easy':   '🟢 Oson',
    'medium': "🟡 O'rta",
    'hard':   '🔴 Qiyin',
    'mixed':  '🎲 Aralash'
}

def compress_questions(q_list: list) -> str:
    """Savollarni compress qilib base64 ga o'girish"""
    raw = json.dumps(q_list, ensure_ascii=False, separators=(',', ':'))
    compressed = zlib.compress(raw.encode('utf-8'), level=9)
    return base64.urlsafe_b64encode(compressed).decode('ascii')

def miniapp_keyboard(url: str):
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="🚀 Testni boshlash",
            web_app=WebAppInfo(url=url)
        )
    ]])

def difficulty_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🟢 Oson",    callback_data="mapp_diff:easy"),
            InlineKeyboardButton(text="🟡 O'rta",   callback_data="mapp_diff:medium"),
        ],
        [
            InlineKeyboardButton(text="🔴 Qiyin",   callback_data="mapp_diff:hard"),
            InlineKeyboardButton(text="🎲 Aralash", callback_data="mapp_diff:mixed"),
        ]
    ])

@router.message(F.text == "📝 Testni boshlash")
async def open_miniapp(message: Message, state: FSMContext):
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
        "🎯 <b>Qiyinlik darajasini tanlang:</b>",
        reply_markup=difficulty_keyboard(),
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("mapp_diff:"))
async def send_questions_to_miniapp(callback: CallbackQuery, state: FSMContext):
    difficulty = callback.data.split(":")[1]

    # Bazadan savollarni olish
    questions = get_random_questions(subject="ona_tili", count=30, difficulty=difficulty)

    if not questions:
        await callback.answer("❌ Bu darajada savollar yo'q!", show_alert=True)
        return

    # Minimal JSON — faqat kerakli fieldlar
    q_list = [
        {
            "id": q['id'],
            "t":  q['question_text'],
            "a":  q['option_a'],
            "b":  q['option_b'],
            "c":  q['option_c'],
            "d":  q['option_d'],
            "ok": q['correct_answer'],
            "img": q['image_file_id'] or ""
        }
        for q in questions
    ]

    # Compress + base64 → URL hash ga yuborish
    encoded = compress_questions(q_list)
    url = f"{config.MINI_APP_URL}#{encoded}"

    diff_label = DIFFICULTY_NAMES.get(difficulty, difficulty)

    await callback.message.edit_text(
        f"📚 <b>Ona tili va Adabiyot Testi</b>\n\n"
        f"🎯 Daraja: <b>{diff_label}</b>\n"
        f"📊 Savollar: <b>{len(q_list)} ta</b>\n\n"
        f"Pastdagi tugmani bosib testni boshlang 👇",
        reply_markup=miniapp_keyboard(url),
        parse_mode="HTML"
    )
    await callback.answer()

@router.message(F.web_app_data)
async def receive_miniapp_data(message: Message, bot: Bot):
    """Mini App dan natija qabul qilish"""
    try:
        data    = json.loads(message.web_app_data.data)
        correct = data.get('correct', 0)
        wrong   = data.get('wrong', 0)
        skip    = data.get('skip', 0)
        total   = data.get('total', 30)
        pct     = data.get('score', 0)

        from datetime import datetime
        save_test_result(
            telegram_id=message.from_user.id,
            correct=correct,
            wrong=wrong,
            started_at=datetime.now().isoformat(),
            difficulty="mixed"
        )

        if pct >= 90:   grade, emoji = "A'lo (5)",       "🏆"
        elif pct >= 70: grade, emoji = "Yaxshi (4)",      "🎉"
        elif pct >= 50: grade, emoji = "Qoniqarli (3)",   "📚"
        else:           grade, emoji = "Qoniqarsiz (2)",  "😔"

        encouragement = "🌟 Ajoyib! Shunday davom eting!" if pct >= 70 else "📖 Ko'proq mashq qiling!"

        await message.answer(
            f"{emoji} <b>Test natijasi saqlandi!</b>\n\n"
            f"━━━━━━━━━━━━━\n"
            f"✅ To'g'ri: <b>{correct}/{total}</b>\n"
            f"❌ Xato: <b>{wrong}/{total}</b>\n"
            f"⏭ O'tkazildi: <b>{skip}</b>\n"
            f"📈 Ball: <b>{pct}%</b>\n"
            f"🎓 Baho: <b>{grade}</b>\n"
            f"━━━━━━━━━━━━━\n\n"
            f"{encouragement}",
            reply_markup=main_menu_keyboard(is_paid=True),
            parse_mode="HTML"
        )

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