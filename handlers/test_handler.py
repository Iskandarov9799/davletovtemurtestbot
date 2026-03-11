from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from database.db import (
    is_registered, get_access_status, mark_free_used,
    has_attestation, get_attestation_format,
    get_questions, count_questions
)
from keyboards.keyboards import (
    onatili_category_keyboard, onatili_topics_keyboard,
    adabiyot_category_keyboard, grades_keyboard,
    difficulty_keyboard, retry_buy_keyboard,
    attestation_buy_keyboard, attestation_format_keyboard,
    miniapp_keyboard, main_menu_keyboard
)
from config import config

router = Router()

# ══════════════════════════════════════════════
# YORDAMCHI FUNKSIYALAR
# ══════════════════════════════════════════════

def make_access_key(subject: str, category: str,
                    subcategory: str = None, difficulty: str = None) -> str:
    """
    Unikal kalit yaratish — access tekshirish uchun
    Masalan: 'onatili:mavzu:fonetika:easy'
             'adabiyot:sinf:7:medium'
             'onatili:aralash:None:hard'
    """
    return f"{subject}:{category}:{subcategory}:{difficulty}"

import json, base64, zlib

def encode_questions(q_list: list, meta: dict = None) -> str:
    """Savollar + meta ma'lumotlarni compress qilib URL hash uchun encode qilish"""
    payload = {'meta': meta or {}, 'questions': q_list}
    raw = json.dumps(payload, ensure_ascii=False, separators=(',', ':'))
    compressed = zlib.compress(raw.encode('utf-8'), level=9)
    return base64.urlsafe_b64encode(compressed).decode('ascii')

def questions_to_miniapp(questions: list) -> list:
    """SQLAlchemy object → Mini App uchun dict"""
    return [
        {
            "id":  q.id,
            "t":   q.question_text,
            "a":   q.option_a,
            "b":   q.option_b,
            "c":   q.option_c,
            "d":   q.option_d,
            "ok":  q.correct_answer,
            "img": q.image_file_id or ""
        }
        for q in questions
    ]

async def safe_edit(callback: CallbackQuery, text: str, reply_markup=None):
    """edit_text — xuddi shu matn bo'lsa xatoni e'tiborsiz qoldiradi"""
    try:
        await callback.message.edit_text(
            text, reply_markup=reply_markup, parse_mode="HTML"
        )
    except Exception as e:
        if "message is not modified" not in str(e):
            raise

async def send_miniapp(callback: CallbackQuery, subject: str, category: str,
                        subcategory: str = None, difficulty: str = None,
                        is_attestation: bool = False):
    """Savollarni bazadan olib Mini App ga yuborish"""
    SUBJ = {'onatili': '📚 Ona tili', 'adabiyot': '📖 Adabiyot'}
    DIFF = {'easy': '🟢 Oson', 'medium': "🟡 O'rta", 'hard': '🔴 Qiyin'}

    # Savollar sonini tekshirish
    cnt = await count_questions(
        subject=subject, category=category,
        subcategory=subcategory, difficulty=difficulty,
        is_attestation=is_attestation
    )

    if cnt == 0 and not is_attestation:
        sub_label  = f" › {subcategory}" if subcategory else ''
        diff_label = DIFF.get(difficulty, '') if difficulty else ''
        await safe_edit(
            callback,
            f"📭 <b>{SUBJ.get(subject,'')}{sub_label}</b> {diff_label}\n\n"
            f"Bu bo'limda hozircha savollar yo'q.\n\n"
            f"⏳ Tez orada qo'shiladi!",
        )
        await callback.answer()
        return

    # Savollarni olish — bor bo'lsa barchasi (max 35)
    questions = await get_questions(
        subject=subject, category=category,
        subcategory=subcategory, difficulty=difficulty,
        count=config.ATTESTATION_COUNT if is_attestation else min(cnt, config.ATTESTATION_COUNT),
        is_attestation=is_attestation
    )

    if not questions:
        await safe_edit(callback, "📭 Savollar topilmadi. Tez orada qo'shiladi!")
        await callback.answer()
        return

    # Encode → URL hash (meta bilan birga)
    meta = {
        'subject':        subject,
        'category':       category,
        'subcategory':    subcategory,
        'difficulty':     difficulty,
        'is_attestation': is_attestation,
        'solution_url':   config.SOLUTION_URL,
    }
    encoded = encode_questions(questions_to_miniapp(questions), meta)
    url = f"https://iskandarov9799.github.io/davletovtemurtestbot/?data={encoded}"

    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Mini App URL uzunligi: {len(url)} belgi")
    logger.info(f"URL boshi: {url[:150]}")

    subj_label   = SUBJ.get(subject, subject)
    diff_label   = DIFF.get(difficulty, '') if difficulty else ''
    sub_label    = f" › {subcategory}" if subcategory else ''
    attest_label = " › Atestatsiya" if is_attestation else ''

    await safe_edit(
        callback,
        f"{subj_label}<b>{sub_label}{attest_label}</b> {diff_label}\n\n"
        f"📊 Savollar: <b>{len(questions)} ta</b>\n"
        f"{'🔒 Tartib boyicha (random emas)' if is_attestation else '🎲 Random tartibda'}\n\n"
        f"Pastdagi tugmani bosib testni boshlang 👇",
        reply_markup=miniapp_keyboard(url),
    )
    await callback.answer()

# ══════════════════════════════════════════════
# BACK CALLBACKS
# ══════════════════════════════════════════════

@router.callback_query(F.data == "back:main")
async def back_main(callback: CallbackQuery):
    await callback.message.delete()
    await callback.answer()

@router.callback_query(F.data == "back:onatili")
async def back_onatili(callback: CallbackQuery):
    await safe_edit(callback,
        "📚 <b>Ona tili</b>\n\nBo'limni tanlang:",
        reply_markup=onatili_category_keyboard(),
    )
    await callback.answer()

@router.callback_query(F.data == "back:adabiyot")
async def back_adabiyot(callback: CallbackQuery):
    await safe_edit(callback,
        "📖 <b>Adabiyot</b>\n\nBo'limni tanlang:",
        reply_markup=adabiyot_category_keyboard(),
    )
    await callback.answer()

# ══════════════════════════════════════════════
# ONA TILI — kategoriya
# ══════════════════════════════════════════════

@router.callback_query(F.data == "onatili:mavzu")
async def onatili_mavzu(callback: CallbackQuery):
    await safe_edit(callback,
        "📌 <b>Mavzulashtirilgan testlar</b>\n\nMavzuni tanlang:",
        reply_markup=onatili_topics_keyboard(),
    )
    await callback.answer()

@router.callback_query(F.data == "onatili:aralash")
async def onatili_aralash(callback: CallbackQuery):
    await safe_edit(callback,
        "🎲 <b>Ona tili — Aralash</b>\n\nQiyinlik darajasini tanlang:",
        reply_markup=difficulty_keyboard("onatili:aralash"),
    )
    await callback.answer()

@router.callback_query(F.data == "onatili:attestation")
async def onatili_attestation(callback: CallbackQuery):
    tid = callback.from_user.id

    if await has_attestation(tid, 'onatili'):
        fmt = await get_attestation_format(tid, 'onatili')
        if fmt == 'miniapp':
            await send_miniapp(callback, 'onatili', 'attestation',
                               is_attestation=True)
        else:
            await send_pdf_attestation(callback, 'onatili')
    else:
        await safe_edit(callback,
            "🎓 <b>Ona tili Atestatsiya</b>\n\n"
            "📋 35 ta belgilangan savol (random emas)\n"
            "💳 Bir martalik to'lov\n\n"
            f"💰 Narxi: <b>{config.PRICE_ATTESTATION:,} so'm</b>",
            reply_markup=attestation_buy_keyboard('onatili'),
        )
    await callback.answer()

# ── Ona tili mavzu tanlash ───────────────────

@router.callback_query(F.data.regexp(r"^onatili:topic:[^:]+$"))
async def onatili_topic(callback: CallbackQuery):
    # onatili:topic:fonetika  (difficulty YO'Q — faqat 3 qism)
    topic = callback.data.split(":")[2]
    topic_label = config.ONA_TILI_TOPICS.get(topic, topic)

    await safe_edit(callback,
        f"📌 <b>{topic_label}</b>\n\nQiyinlik darajasini tanlang:",
        reply_markup=difficulty_keyboard(f"onatili:topic:{topic}"),
    )
    await callback.answer()

# ══════════════════════════════════════════════
# ADABIYOT — kategoriya
# ══════════════════════════════════════════════

@router.callback_query(F.data == "adabiyot:sinf")
async def adabiyot_sinf(callback: CallbackQuery):
    await safe_edit(callback,
        "🏫 <b>Sinflar bo'yicha test</b>\n\nSinfni tanlang:",
        reply_markup=grades_keyboard(),
    )
    await callback.answer()

@router.callback_query(F.data == "adabiyot:aralash")
async def adabiyot_aralash(callback: CallbackQuery):
    await safe_edit(callback,
        "🎲 <b>Adabiyot — Aralash</b>\n\nQiyinlik darajasini tanlang:",
        reply_markup=difficulty_keyboard("adabiyot:aralash"),
    )
    await callback.answer()

@router.callback_query(F.data == "adabiyot:gazallar")
async def adabiyot_gazallar(callback: CallbackQuery):
    await safe_edit(callback,
        "📜 <b>G'azallar</b>\n\nQiyinlik darajasini tanlang:",
        reply_markup=difficulty_keyboard("adabiyot:gazallar"),
    )
    await callback.answer()

@router.callback_query(F.data == "adabiyot:attestation")
async def adabiyot_attestation(callback: CallbackQuery):
    tid = callback.from_user.id

    if await has_attestation(tid, 'adabiyot'):
        fmt = await get_attestation_format(tid, 'adabiyot')
        if fmt == 'miniapp':
            await send_miniapp(callback, 'adabiyot', 'attestation',
                               is_attestation=True)
        else:
            await send_pdf_attestation(callback, 'adabiyot')
    else:
        await safe_edit(callback,
            "🎓 <b>Adabiyot Atestatsiya</b>\n\n"
            "📋 35 ta belgilangan savol (random emas)\n"
            "💳 Bir martalik to'lov\n\n"
            f"💰 Narxi: <b>{config.PRICE_ATTESTATION:,} so'm</b>",
            reply_markup=attestation_buy_keyboard('adabiyot'),
        )
    await callback.answer()

# ── Adabiyot sinf tanlash ────────────────────

@router.callback_query(F.data.regexp(r"^adabiyot:grade:\d+$"))
async def adabiyot_grade(callback: CallbackQuery):
    # adabiyot:grade:7
    grade = callback.data.split(":")[2]
    grade_label = config.GRADES.get(grade, grade)

    await safe_edit(callback,
        f"🏫 <b>{grade_label}</b>\n\nQiyinlik darajasini tanlang:",
        reply_markup=difficulty_keyboard(f"adabiyot:grade:{grade}"),
    )
    await callback.answer()

# ══════════════════════════════════════════════
# QIYINLIK TANLANDI → ACCESS TEKSHIRISH
# ══════════════════════════════════════════════
# Callback data formatlari:
#   onatili:aralash:easy
#   onatili:topic:fonetika:easy
#   adabiyot:aralash:medium
#   adabiyot:grade:7:hard
#   adabiyot:gazallar:easy

@router.callback_query(F.data.regexp(
    r"^(onatili|adabiyot):(aralash|gazallar|topic\:\w+|grade\:\d+):(easy|medium|hard)$"
))
async def difficulty_chosen(callback: CallbackQuery):
    tid  = callback.from_user.id
    parts = callback.data.split(":")
    # parts[0] = subject
    # parts[1] = category  (yoki 'topic' / 'grade')
    # parts[-1] = difficulty

    subject    = parts[0]
    difficulty = parts[-1]

    # Category va subcategory ajratish
    if parts[1] == 'topic':
        category    = 'mavzu'
        subcategory = parts[2]
    elif parts[1] == 'grade':
        category    = 'sinf'
        subcategory = parts[2]
    elif parts[1] == 'aralash':
        category    = 'aralash'
        subcategory = None
    elif parts[1] == 'gazallar':
        category    = 'gazallar'
        subcategory = None
    else:
        category    = parts[1]
        subcategory = None

    access_key = make_access_key(subject, category, subcategory, difficulty)

    # Ro'yxatdan o'tganmi tekshirish
    if not await is_registered(tid):
        await safe_edit(callback,
            "👤 <b>Ro'yxatdan o'tmagansiz!</b>\n\n"
            "Testdan foydalanish uchun avval ro'yxatdan o'ting.\n"
            "📱 /start buyrug'ini yuboring."
        )
        await callback.answer()
        return

    status = await get_access_status(tid, access_key)

    if status == 'free':
        # Bepul urinish — belgilash va testni boshlash
        await mark_free_used(tid, access_key)
        await send_miniapp(
            callback, subject, category,
            subcategory=subcategory, difficulty=difficulty
        )

    elif status == 'paid':
        # To'lov tasdiqlangan — testni boshlash
        await send_miniapp(
            callback, subject, category,
            subcategory=subcategory, difficulty=difficulty
        )

    else:
        # To'lov kerak
        SUBJ = {'onatili': '📚 Ona tili', 'adabiyot': '📖 Adabiyot'}
        DIFF = {'easy': '🟢 Oson', 'medium': "🟡 O'rta", 'hard': '🔴 Qiyin'}
        sub_label = f" › {subcategory}" if subcategory else ''

        await safe_edit(callback,
            f"🔒 <b>Birinchi urinishingizni allaqachon ishlatgansiz!</b>\n\n"
            f"📚 {SUBJ.get(subject, subject)}{sub_label} {DIFF.get(difficulty,'')}\n\n"
            f"Qayta urinish uchun to'lov qiling:\n"
            f"💰 <b>{config.PRICE_RETRY:,} so'm</b>",
            reply_markup=retry_buy_keyboard(access_key),
        )
    await callback.answer()

# ══════════════════════════════════════════════
# ATESTATSIYA FORMAT
# ══════════════════════════════════════════════

@router.callback_query(F.data.startswith("attest_fmt:"))
async def attestation_format_chosen(callback: CallbackQuery):
    # attest_fmt:onatili:miniapp
    _, subject, fmt = callback.data.split(":")

    from database.db import grant_attestation
    await grant_attestation(callback.from_user.id, subject, fmt)

    if fmt == 'miniapp':
        await send_miniapp(callback, subject, 'attestation', is_attestation=True)
    else:
        await send_pdf_attestation(callback, subject)

    await callback.answer()

# ══════════════════════════════════════════════
# PDF ATESTATSIYA (placeholder)
# ══════════════════════════════════════════════

async def send_pdf_attestation(callback: CallbackQuery, subject: str):
    """PDF formatda atestatsiya — keyingi bosqichda to'liq amalga oshiriladi"""
    SUBJ = {'onatili': 'Ona tili', 'adabiyot': 'Adabiyot'}
    await safe_edit(callback,
        f"📄 <b>{SUBJ.get(subject, subject)} Atestatsiya — PDF</b>\n\n"
        f"⏳ PDF tayyorlanmoqda...\n"
        f"Tez orada yuboriladi!",
    )

# ══════════════════════════════════════════════
# MINI APP NATIJA QABUL QILISH
# ══════════════════════════════════════════════

@router.message(F.web_app_data)
async def receive_miniapp_result(message: Message):
    import json
    from database.db import save_test_result

    try:
        data = json.loads(message.web_app_data.data)
        correct = data.get('correct', 0)
        wrong   = data.get('wrong', 0)
        skipped = data.get('skip', 0)
        total   = data.get('total', 35)
        pct     = data.get('score', 0)

        # FSM da saqlangan meta ma'lumotlar yo'q (hash orqali yuborilgan)
        # Shuning uchun subject/category ni data dan olamiz
        subject        = data.get('subject', 'onatili')
        category       = data.get('category', 'aralash')
        subcategory    = data.get('subcategory')
        difficulty     = data.get('difficulty')
        is_attestation = data.get('is_attestation', False)

        score = await save_test_result(
            telegram_id=message.from_user.id,
            subject=subject, category=category,
            subcategory=subcategory, difficulty=difficulty,
            correct=correct, wrong=wrong, skipped=skipped,
            is_attestation=is_attestation
        )

        # Baho
        if pct >= 90:   grade, emoji = "A'lo (5)",      "🏆"
        elif pct >= 70: grade, emoji = "Yaxshi (4)",     "🎉"
        elif pct >= 50: grade, emoji = "Qoniqarli (3)",  "📚"
        else:           grade, emoji = "Qoniqarsiz (2)", "😔"

        encouragement = "🌟 Ajoyib! Shunday davom eting!" if pct >= 70 \
                        else "📖 Ko'proq mashq qiling!"

        await message.answer(
            f"{emoji} <b>Test natijasi saqlandi!</b>\n\n"
            f"━━━━━━━━━━━━━\n"
            f"✅ To'g'ri:    <b>{correct}/{total}</b>\n"
            f"❌ Xato:       <b>{wrong}/{total}</b>\n"
            f"⏭ O'tkazildi: <b>{skipped}</b>\n"
            f"📈 Ball:       <b>{pct}%</b>\n"
            f"🎓 Baho:       <b>{grade}</b>\n"
            f"━━━━━━━━━━━━━\n\n"
            f"{encouragement}",
            reply_markup=main_menu_keyboard(),
        )

        # Adminlarga xabar
        from aiogram import Bot
        from aiogram.client.default import DefaultBotProperties
        from aiogram.enums import ParseMode
        bot = message.bot
        for admin_id in config.ADMIN_IDS:
            try:
                await bot.send_message(
                    chat_id=admin_id,
                    text=(
                        f"📊 Yangi natija\n"
                        f"👤 {message.from_user.full_name}\n"
                        f"📈 {pct}% ({correct}/{total})"
                    )
                )
            except Exception:
                pass

    except Exception as e:
        await message.answer(f"❌ Natijani saqlashda xato: {e}")