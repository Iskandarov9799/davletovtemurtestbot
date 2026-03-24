import json
import base64
import zlib
import logging
from aiogram import Router, F, Bot
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
)
from aiogram.fsm.context import FSMContext

from database.db import (
    is_registered,
    get_access_status,
    get_questions,
    save_test_result,
    mark_wrong_question,
    mark_correct_question,
)
from keyboards.keyboards import main_menu_keyboard
from config import config

logger = logging.getLogger(__name__)
router = Router()

DIFFICULTY_NAMES = {
    'easy':   '🟢 Oson',
    'medium': "🟡 O'rta",
    'hard':   '🔴 Qiyin',
    'mixed':  '🎲 Aralash',
}


def compress_questions(data: dict | list) -> str:
    """Savollarni compress qilib base64 ga o'girish"""
    raw        = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
    compressed = zlib.compress(raw.encode('utf-8'), level=9)
    return base64.urlsafe_b64encode(compressed).decode('ascii')


def miniapp_keyboard(url: str):
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🚀 Testni boshlash", web_app=WebAppInfo(url=url))
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
        ],
    ])


@router.message(F.text == "📝 Testni boshlash")
async def open_miniapp(message: Message, state: FSMContext):
    uid = message.from_user.id
    if not await is_registered(uid):
        await message.answer("❌ Avval ro'yxatdan o'ting! /start")
        return
    status = await get_access_status(uid, access_key="onatili_test")
    if status == 'buy':
        await message.answer(
            "❌ Test uchun to'lov qilishingiz kerak!\n💳 /pay buyrug'ini yuboring.",
            reply_markup=main_menu_keyboard(),
        return
    await message.answer(
        "🎯 <b>Qiyinlik darajasini tanlang:</b>",
        reply_markup=difficulty_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("mapp_diff:"))
async def send_questions_to_miniapp(callback: CallbackQuery, state: FSMContext):
    difficulty = callback.data.split(":")[1]
    questions = await get_questions(
        subject='onatili',
        category=difficulty if difficulty != 'mixed' else 'aralash',
        difficulty=difficulty if difficulty != 'mixed' else None,
        count=30,
        telegram_id=callback.from_user.id,
    )

    if not questions:
        await callback.answer("❌ Bu darajada savollar yo'q!", show_alert=True)
        return

    q_list = [
        {
            "id":  q['id'],
            "t":   q['question_text'],
            "a":   q['option_a'],
            "b":   q['option_b'],
            "c":   q['option_c'],
            "d":   q['option_d'],
            "ok":  q['correct_answer'],
            "img": q.get('image_file_id') or "",
        }
        for q in questions
    ]

    # meta + questions birgalikda yuboriladi — web_app_handler da subject/category kerak
    payload = {
        "questions": q_list,
        "meta": {
            "subject":    "onatili",
            "category":   DIFFICULTY_NAMES.get(difficulty, difficulty),
            "difficulty": difficulty,
            "is_attestation": False,
        }
    }

    encoded    = compress_questions(payload)
    url        = f"{config.MINI_APP_URL}#{encoded}"
    diff_label = DIFFICULTY_NAMES.get(difficulty, difficulty)

    await callback.message.edit_text(
        f"📚 <b>Ona tili va Adabiyot Testi</b>\n\n"
        f"🎯 Daraja: <b>{diff_label}</b>\n"
        f"📊 Savollar: <b>{len(q_list)} ta</b>\n\n"
        f"Pastdagi tugmani bosib testni boshlang 👇",
        reply_markup=miniapp_keyboard(url),
        parse_mode="HTML",
    )
    await callback.answer()


# ══════════════════════════════════════════════
# NATIJA QABUL QILISH — tg.sendData() dan keladi
# ══════════════════════════════════════════════
@router.message(F.web_app_data)
async def receive_miniapp_data(message: Message, bot: Bot):
    user_id  = message.from_user.id
    username = message.from_user.username
    uname    = f"@{username}" if username else message.from_user.full_name

    logger.info(f"📥 web_app_data keldi: user={user_id}")

    # ── JSON parse ──────────────────────────────
    try:
        data = json.loads(message.web_app_data.data)
    except Exception as e:
        logger.error(f"JSON parse xato: {e}")
        await message.answer("❌ Natija o'qishda xato. Qaytadan urinib ko'ring.")
        return

    correct        = int(data.get('correct',  0))
    wrong          = int(data.get('wrong',    0))
    skipped        = int(data.get('skip',     0))
    total          = int(data.get('total',    0))
    pct            = float(data.get('score',  0))
    subject        = data.get('subject',      'onatili')
    category       = data.get('category',     'aralash')
    subcategory    = data.get('subcategory')
    difficulty     = data.get('difficulty')
    is_attestation = bool(data.get('is_attestation', False))
    wrong_ids      = data.get('wrong_ids',   [])
    correct_ids    = data.get('correct_ids', [])

    logger.info(f"Natija: {correct}/{total} ({pct}%) | user={user_id}")

    # ── Baho ────────────────────────────────────
    if   pct >= 90: grade, emoji = "A'lo (5)",      "🏆"
    elif pct >= 70: grade, emoji = "Yaxshi (4)",     "🎉"
    elif pct >= 50: grade, emoji = "Qoniqarli (3)",  "📚"
    else:           grade, emoji = "Qoniqarsiz (2)", "😔"

    encouragement = "🌟 Ajoyib! Shunday davom eting!" if pct >= 70 else "📖 Ko'proq mashq qiling!"

    # ── Guruhga yuborish (DB dan oldin — crash bo'lsa ham yuborilsin) ──
    if config.RESULT_GROUP_ID:
        SUBJ = {
            'onatili':     '📚 Ona tili',
            'adabiyot':    '📖 Adabiyot',
            'attestation': '🎓 Attestatsiya',
            'milliy':      '🏅 Milliy sertifikat',
        }
        subj_label = SUBJ.get(subject, subject)
        cat_label  = f" › {subcategory}" if subcategory else (f" › {category}" if category else "")
        try:
            group_id = int(config.RESULT_GROUP_ID)
            await bot.send_message(
                chat_id    = group_id,
                text       = (
                    f"{emoji} <b>{uname}</b>
"
                    f"📌 {subj_label}{cat_label}
"
                    f"✅ {correct}/{total} | 📈 {pct:.0f}% | 🎓 {grade}"
                ),
                parse_mode = "HTML",
            )
            logger.info(f"✅ Guruhga yuborildi: {group_id}")
        except Exception as e:
            logger.error(f"❌ Guruhga yuborishda xato: {e!r}")
    else:
        logger.warning("⚠️ RESULT_GROUP_ID .env da yo'q — guruhga yuborilmadi")

    # ── DB ga saqlash ────────────────────────────
    try:
        await save_test_result(
            telegram_id    = user_id,
            subject        = subject,
            category       = category,
            subcategory    = subcategory,
            difficulty     = difficulty,
            correct        = correct,
            wrong          = wrong,
            skipped        = skipped,
            is_attestation = is_attestation,
        )
        logger.info(f"✅ DB ga saqlandi: user={user_id}")
    except Exception as e:
        logger.error(f"❌ save_test_result xato: {e!r}")

    for qid in wrong_ids:
        try:
            await mark_wrong_question(user_id, int(qid))
        except Exception as e:
            logger.warning(f"mark_wrong xato qid={qid}: {e}")

    for qid in correct_ids:
        try:
            await mark_correct_question(user_id, int(qid))
        except Exception as e:
            logger.warning(f"mark_correct xato qid={qid}: {e}")

    # ── Foydalanuvchiga natija ───────────────────
    try:
        await message.answer(
            f"{emoji} <b>Test natijasi saqlandi!</b>\n\n"
            f"━━━━━━━━━━━━━\n"
            f"✅ To'g'ri:     <b>{correct}/{total}</b>\n"
            f"❌ Xato:        <b>{wrong}/{total}</b>\n"
            f"⏭ O'tkazildi: <b>{skipped}</b>\n"
            f"📈 Ball:        <b>{pct:.0f}%</b>\n"
            f"🎓 Baho:        <b>{grade}</b>\n"
            f"━━━━━━━━━━━━━\n\n"
            f"{encouragement}",
            reply_markup=main_menu_keyboard(),
            parse_mode="HTML",
        )
    except Exception as e:
        logger.error(f"answer xato: {e!r}")