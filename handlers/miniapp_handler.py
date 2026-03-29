import json
import logging
from aiogram import Router, F, Bot
from aiogram.types import Message

from database.db import (
    is_registered,
    get_user,
    save_test_result,
    mark_wrong_question,
    mark_correct_question,
)
from keyboards.keyboards import main_menu_keyboard
from config import config

logger = logging.getLogger(__name__)
router = Router()

# ══════════════════════════════════════════════
# NATIJA QABUL QILISH — tg.sendData() dan keladi
# ══════════════════════════════════════════════

def _attestation_grade(pct: float) -> tuple[str, str]:
    """
    59 gacha   → Mutaxassis
    60-68      → 2-toifa
    70-78      → 1-toifa
    80-85      → Oliy toifa
    86+        → 70% ustama
    """
    if pct <= 59:
        return "Mutaxassis", "📋"
    elif pct <= 68:
        return "2-toifa", "🥉"
    elif pct <= 78:
        return "1-toifa", "🥈"
    elif pct <= 85:
        return "Oliy toifa", "🥇"
    else:
        return "70% ustama", "🏆"


@router.message(F.web_app_data)
async def receive_miniapp_data(message: Message, bot: Bot):
    user_id  = message.from_user.id
    username = message.from_user.username

    logger.info(f"📥 web_app_data keldi: user={user_id}")

    # ── Foydalanuvchi ismini olish ──────────────
    user = await get_user(user_id)
    if user and user.full_name:
        full_name = user.full_name
    else:
        full_name = message.from_user.full_name or "Noma'lum"

    uname_link = f"@{username}" if username else full_name

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

    # ── Baho hisoblash ──────────────────────────
    SUBJ_LABELS = {
        'onatili':     '📚 Ona tili',
        'adabiyot':    '📖 Adabiyot',
        'attestation': '🎓 Attestatsiya',
        'milliy':      '🏅 Milliy sertifikat',
    }
    subj_label = SUBJ_LABELS.get(subject, subject)

    # grade_label va grade_emoji — har ikkala blokda ham mavjud bo'lsin
    grade_label, grade_emoji = _attestation_grade(pct)
    encouragement = "🌟 Ajoyib natija!" if pct >= 70 else "📖 Ko'proq mashq qiling!"

    # ── Kategoriya nomi ─────────────────────────
    # subcategory chiroyli nom: bolim_1 → 1-bo'lim
    if subcategory and subcategory.startswith('bolim_'):
        bolim_num  = subcategory.split('_', 1)[1]
        cat_label  = f" › {bolim_num}-bo'lim"
    elif subcategory:
        cat_label  = f" › {subcategory}"
    elif category:
        cat_label  = f" › {category}"
    else:
        cat_label  = ""

    # ── Guruhga yuborish ─────────────────────────
    if config.RESULT_GROUP_ID:
        try:
            group_id = int(config.RESULT_GROUP_ID)
            if is_attestation or subject in ('attestation', 'milliy'):
                grade_label, grade_emoji = _attestation_grade(pct)
                group_text = (
                    f"{grade_emoji} <b>{full_name}</b> ({uname_link})\n"
                    f"📌 {subj_label}{cat_label}\n"
                    f"✅ {correct}/{total} | 📈 {pct:.0f}% | 🎓 {grade_label}"
                )
            else:
                group_text = (
                    f"{grade_emoji} <b>{full_name}</b> ({uname_link})\n"
                    f"📌 {subj_label}{cat_label}\n"
                    f"✅ {correct}/{total} | 📈 {pct:.0f}% | 🎓 {grade}"
                )
            await bot.send_message(
                chat_id    = group_id,
                text       = group_text,
                parse_mode = "HTML",
            )
            logger.info(f"✅ Guruhga yuborildi: {group_id}")
        except Exception as e:
            logger.error(f"❌ Guruhga yuborishda xato: {e!r}")
    else:
        logger.warning("⚠️ RESULT_GROUP_ID .env da yo'q — guruhga yuborilmadi")

    # ── DB ga saqlash ────────────────────────────
    attempt_num = 1  # fallback
    try:
        _result = await save_test_result(
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
        # save_test_result score qaytaradi; attempt_num ni alohida hisoblaymiz
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

    # ── Foydalanuvchiga natija (tepada ism) ──────
    try:
        result_text = (
            f"👤 <b>{full_name}</b>\n"
            f"━━━━━━━━━━━━━\n"
            f"📌 {subj_label}{cat_label}\n"
            f"━━━━━━━━━━━━━\n"
            f"✅ To'g'ri:     <b>{correct}/{total}</b>\n"
            f"❌ Xato:        <b>{wrong}/{total}</b>\n"
            f"⏭ O'tkazildi: <b>{skipped}</b>\n"
            f"📈 Ball:        <b>{pct:.0f}%</b>\n"
            f"━━━━━━━━━━━━━\n"
            f"{grade_emoji} <b>Daraja: {grade_label}</b>\n"
            f"━━━━━━━━━━━━━\n\n"
            f"{encouragement}\n"
            f"📊 {attempt_num}-urinish"
        )
        await message.answer(
            result_text,
            reply_markup=main_menu_keyboard(),
            parse_mode="HTML",
        )
    except Exception as e:
        logger.error(f"answer xato: {e!r}")