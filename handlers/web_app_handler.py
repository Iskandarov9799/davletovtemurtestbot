"""
handlers/web_app_handler.py

GitHub Pages miniapp → tg.sendData() → SHU HANDLER → DB

Bot tomonida qo'shish kerak:
    from handlers import web_app_handler
    dp.include_router(web_app_handler.router)
"""

import json
import logging
from aiogram import Router, F
from aiogram.types import Message

logger = logging.getLogger(__name__)
router = Router()


@router.message(F.web_app_data)
async def on_web_app_data(message: Message):
    """
    Miniapp tg.sendData() chaqirganda shu handler ishlaydi.
    message.web_app_data.data — JSON string
    """
    user_id = message.from_user.id
    logger.info(f"📥 web_app_data keldi: user={user_id}")

    # ── JSON parse ──────────────────────────────
    try:
        raw  = message.web_app_data.data
        data = json.loads(raw)
    except Exception as e:
        logger.error(f"JSON parse xato: {e} | raw: {message.web_app_data.data[:200]}")
        await message.answer("❌ Natija o'qishda xato. Qaytadan urinib ko'ring.")
        return

    # ── Qiymatlarni olish ───────────────────────
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
    wrong_ids      = data.get('wrong_ids',  [])
    correct_ids    = data.get('correct_ids', [])

    logger.info(
        f"Natija: user={user_id} | {correct}/{total} | {pct}% | "
        f"sub={subject} | cat={category}"
    )

    # ── DB ga saqlash ────────────────────────────
    from database.db import (
        save_test_result,
        mark_wrong_question,
        mark_correct_question,
    )

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
        logger.error(f"❌ save_test_result xato: {e}")
        # DB xatosi bo'lsa ham foydalanuvchiga javob beramiz

    # Xato savol IDlarini belgilash
    for qid in wrong_ids:
        try:
            await mark_wrong_question(user_id, int(qid))
        except Exception as e:
            logger.warning(f"mark_wrong xato (qid={qid}): {e}")

    # To'g'ri savol IDlarini belgilash
    for qid in correct_ids:
        try:
            await mark_correct_question(user_id, int(qid))
        except Exception as e:
            logger.warning(f"mark_correct xato (qid={qid}): {e}")

    # ── Baho ────────────────────────────────────
    if   pct >= 90: grade, emoji = "A'lo (5)",      "🏆"
    elif pct >= 70: grade, emoji = "Yaxshi (4)",     "🎉"
    elif pct >= 50: grade, emoji = "Qoniqarli (3)",  "📚"
    else:           grade, emoji = "Qoniqarsiz (2)", "😔"

    # ── Foydalanuvchiga natija xabari ────────────
    from keyboards.keyboards import main_menu_keyboard

    SUBJ_LABELS = {
        'onatili':  '📚 Ona tili',
        'adabiyot': '📖 Adabiyot',
    }
    subj_label = SUBJ_LABELS.get(subject, subject)

    try:
        await message.answer(
            text = (
                f"{emoji} <b>Test natijasi!</b>\n"
                f"<i>{subj_label} — {category}</i>\n\n"
                f"━━━━━━━━━━━━━\n"
                f"✅ To'g'ri:     <b>{correct}/{total}</b>\n"
                f"❌ Xato:        <b>{wrong}/{total}</b>\n"
                f"⏭ O'tkazildi: <b>{skipped}</b>\n"
                f"📈 Ball:        <b>{pct:.0f}%</b>\n"
                f"🎓 Baho:        <b>{grade}</b>\n"
                f"━━━━━━━━━━━━━"
            ),
            reply_markup = main_menu_keyboard(),
            parse_mode   = "HTML",
        )
    except Exception as e:
        logger.error(f"answer xato: {e}")

    # ── Guruhga yuborish ─────────────────────────
    from config import config
    if config.RESULT_GROUP_ID:
        username = message.from_user.username
        uname    = f"@{username}" if username else message.from_user.full_name
        try:
            await message.bot.send_message(
                chat_id    = int(config.RESULT_GROUP_ID),
                text       = (
                    f"{emoji} <b>{uname}</b> — {subj_label}\n"
                    f"✅ {correct}/{total} | 📈 {pct:.0f}% | 🎓 {grade}"
                ),
                parse_mode = "HTML",
            )
        except Exception as e:
            logger.warning(f"Guruhga yuborishda xato: {e}")