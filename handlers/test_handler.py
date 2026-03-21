import json, base64, zlib, logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message

from database.db import (
    is_registered, get_access_status, mark_free_used, mark_once_used,
    has_attestation, get_attestation_format,
    get_questions, count_questions,
    mark_wrong_question, mark_correct_question
)
from keyboards.keyboards import (
    onatili_category_keyboard, onatili_bolimlar_keyboard,
    onatili_submavzu_keyboard, adabiyot_category_keyboard,
    adabiyot_boblar_keyboard, grades_keyboard,
    payment_options_keyboard, attestation_buy_standalone_keyboard,
    miniapp_keyboard, main_menu_keyboard
)
from config import config

router = Router()
logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════
# YORDAMCHI FUNKSIYALAR
# ══════════════════════════════════════════════

def make_access_key(subject, category, subcategory=None):
    return f"{subject}:{category}:{subcategory}"

def encode_questions(q_list, meta=None):
    payload = {'meta': meta or {}, 'questions': q_list}
    raw = json.dumps(payload, ensure_ascii=False, separators=(',', ':'))
    return base64.urlsafe_b64encode(zlib.compress(raw.encode(), level=9)).decode()

def questions_to_miniapp(questions):
    """Rasmlar hali file_id — URL ga aylantirilmagan"""
    return [{"id": q.id, "t": q.question_text, "a": q.option_a,
             "b": q.option_b, "c": q.option_c, "d": q.option_d,
             "ok": q.correct_answer, "img": q.image_file_id or "",
             "type": getattr(q, 'question_type', 'choice'),
             "parts": getattr(q, 'written_parts', 1),
             "kw1": getattr(q, 'keywords_1', None) or "",
             "kw2": getattr(q, 'keywords_2', None) or ""}
            for q in questions]

async def resolve_image_urls(q_list: list, bot) -> list:
    """
    file_id larni doimiy URL ga aylantirish:
    1. Avval DB cache dan tekshiradi (image_url_cache)
    2. Topilmasa — Telegram dan yuklab, Cloudinary ga joylaydi
    3. Cloudinary sozlanmagan bo'lsa — vaqtinchalik Telegram URL ishlatadi
    """
    from config import config
    result = []
    for q in q_list:
        img = q.get("img", "")
        if not img:
            result.append(q)
            continue

        # Allaqachon URL bo'lsa — o'zgartirma
        if img.startswith("http"):
            result.append(q)
            continue

        # Cloudinary sozlanganmi?
        if (getattr(config, 'CLOUDINARY_CLOUD_NAME', '') and
            getattr(config, 'CLOUDINARY_API_KEY', '') and
            getattr(config, 'CLOUDINARY_API_SECRET', '')):
            try:
                url = await upload_to_cloudinary(img, bot, config)
                q = {**q, "img": url}
            except Exception as e:
                logger.warning(f"Cloudinary xato: {e}, Telegram URL ishlatiladi")
                try:
                    file = await bot.get_file(img)
                    url = f"https://api.telegram.org/file/bot{bot.token}/{file.file_path}"
                    q = {**q, "img": url}
                except Exception:
                    q = {**q, "img": ""}
        else:
            # Cloudinary sozlanmagan — vaqtinchalik Telegram URL
            try:
                file = await bot.get_file(img)
                url = f"https://api.telegram.org/file/bot{bot.token}/{file.file_path}"
                q = {**q, "img": url}
            except Exception:
                q = {**q, "img": ""}

        result.append(q)
    return result

# Cache: file_id → cloudinary URL
_image_url_cache: dict = {}

async def upload_to_cloudinary(file_id: str, bot, config) -> str:
    """file_id ni Cloudinary ga yuklaydi, URL qaytaradi. Cache ishlatadi."""
    import aiohttp, io

    # Cache da bormi?
    if file_id in _image_url_cache:
        return _image_url_cache[file_id]

    # Telegram dan yuklab olish
    file      = await bot.get_file(file_id)
    tg_url    = f"https://api.telegram.org/file/bot{bot.token}/{file.file_path}"

    async with aiohttp.ClientSession() as session:
        # Rasmni yuklab olish
        async with session.get(tg_url) as resp:
            img_bytes = await resp.read()

        # Cloudinary ga yuklash
        import hashlib, hmac, time
        timestamp   = str(int(time.time()))
        public_id   = f"bot_imgs/{file_id[:20]}"
        sign_str    = f"public_id={public_id}&timestamp={timestamp}"
        signature   = hmac.new(
            config.CLOUDINARY_API_SECRET.encode(),
            sign_str.encode(), hashlib.sha1
        ).hexdigest()

        form = aiohttp.FormData()
        form.add_field('file',       img_bytes,                    content_type='image/jpeg')
        form.add_field('api_key',    config.CLOUDINARY_API_KEY)
        form.add_field('timestamp',  timestamp)
        form.add_field('public_id',  public_id)
        form.add_field('signature',  signature)

        upload_url = f"https://api.cloudinary.com/v1_1/{config.CLOUDINARY_CLOUD_NAME}/image/upload"
        async with session.post(upload_url, data=form) as resp:
            data = await resp.json()
            if 'secure_url' not in data:
                raise Exception(f"Cloudinary javob: {data}")
            url = data['secure_url']

    # Cache ga saqlash
    _image_url_cache[file_id] = url
    logger.info(f"Cloudinary: {file_id[:10]}... → {url[:50]}...")
    return url

async def safe_edit(callback, text, reply_markup=None):
    try:
        await callback.message.edit_text(text, reply_markup=reply_markup, parse_mode="HTML")
    except Exception as e:
        if "message is not modified" not in str(e):
            pass

async def send_miniapp(callback, subject, category,
                       subcategory=None, is_attestation=False):
    SUBJ = {'onatili': '📚 Ona tili', 'adabiyot': '📖 Adabiyot'}
    tid  = callback.from_user.id
    bot  = callback.bot

    if not await is_registered(tid):
        await safe_edit(callback,
            "👤 <b>Ro'yxatdan o'tmagansiz!</b>\n\n/start buyrug'ini yuboring.")
        await callback.answer()
        return

    cnt = await count_questions(subject=subject, category=category,
                                subcategory=subcategory,
                                is_attestation=is_attestation)
    if cnt == 0:
        await safe_edit(callback,
            "📭 Bu bo'limda hozircha savollar yo'q.\n⏳ Tez orada qo'shiladi!")
        await callback.answer()
        return

    if not is_attestation:
        access_key = make_access_key(subject, category, subcategory)
        status     = await get_access_status(tid, access_key)
        if status == 'buy':
            await safe_edit(callback,
                "🔒 <b>Birinchi bepul urinishingizni ishlatgansiz!</b>\n\n"
                "Davom etish uchun to'lov turini tanlang:",
                reply_markup=payment_options_keyboard(access_key))
            await callback.answer()
            return
        elif status == 'free':
            await mark_free_used(tid, access_key)
        elif status == 'paid':
            await mark_once_used(tid, access_key)
    else:
        pass  # attestation endi send_miniapp orqali emas

    questions = await get_questions(
        subject=subject, category=category,
        subcategory=subcategory, difficulty=None,
        count=config.ATTESTATION_COUNT if is_attestation else min(cnt, config.MAX_QUESTIONS),
        is_attestation=is_attestation,
        telegram_id=tid if not is_attestation else None
    )

    meta = {'subject': subject, 'category': category, 'subcategory': subcategory,
            'is_attestation': is_attestation, 'solution_url': config.SOLUTION_URL}
    q_list = questions_to_miniapp(questions)
    q_list = await resolve_image_urls(q_list, bot)
    encoded = encode_questions(q_list, meta)
    url = f"{config.MINI_APP_URL.rstrip('/')}/?data={encoded}"

    sub_label = f" › {subcategory}" if subcategory else ''
    await safe_edit(callback,
        f"{SUBJ.get(subject)}<b>{sub_label}</b>\n\n"
        f"📊 Savollar: <b>{len(questions)} ta</b>\n"
        f"{'🔒 Tartib bo\'yicha' if is_attestation else '🎲 Random tartibda'}\n\n"
        f"Pastdagi tugmani bosib testni boshlang 👇",
        reply_markup=miniapp_keyboard(url)
    )
    await callback.answer()

# ══════════════════════════════════════════════
# ASOSIY MENYU HANDLERLARI
# ══════════════════════════════════════════════

@router.message(F.text == "📚 Ona tili")
async def onatili_menu(message: Message):
    if not await is_registered(message.from_user.id):
        await message.answer("❗ Avval ro'yxatdan o'ting — /start")
        return
    await message.answer(
        "📚 <b>Ona tili</b>\n\nBo'limni tanlang:",
        reply_markup=onatili_category_keyboard(), parse_mode="HTML"
    )

@router.message(F.text == "📖 Adabiyot")
async def adabiyot_menu(message: Message):
    if not await is_registered(message.from_user.id):
        await message.answer("❗ Avval ro'yxatdan o'ting — /start")
        return
    await message.answer(
        "📖 <b>Adabiyot</b>\n\nBo'limni tanlang:",
        reply_markup=adabiyot_category_keyboard(), parse_mode="HTML"
    )

@router.message(F.text == "🎓 Atestatsiya")
async def attestation_menu(message: Message):
    if not await is_registered(message.from_user.id):
        await message.answer("❗ Avval ro'yxatdan o'ting — /start")
        return
    tid = message.from_user.id

    if await has_attestation(tid, "attestation"):
        cnt = await count_questions(subject="attestation", category="attestation",
                                    is_attestation=True)
        if cnt == 0:
            await message.answer("❌ Attestatsiya savollari hali qo'shilmagan.")
            return
        await _launch_attestation_msg(message, tid)
    else:
        await message.answer(
            "🎓 <b>Atestatsiya</b>\n\n"
            "📋 35 ta belgilangan savol\n"
            "(Ona tili + Adabiyot aralash)\n"
            "💳 Bir martalik to'lov\n\n"
            f"💰 Narxi: <b>{config.PRICE_ATTESTATION:,} so'm</b>",
            reply_markup=attestation_buy_standalone_keyboard(),
            parse_mode="HTML"
        )

async def _launch_attestation_msg(message: Message, tid: int):
    questions = await get_questions(
        subject="attestation", category="attestation",
        is_attestation=True, count=config.ATTESTATION_COUNT
    )
    meta = {
        "subject": "attestation", "category": "attestation",
        "is_attestation": True, "solution_url": config.SOLUTION_URL
    }
    q_list  = questions_to_miniapp(questions)
    q_list  = await resolve_image_urls(q_list, message.bot)
    encoded = encode_questions(q_list, meta)
    url     = f"{config.MINI_APP_URL.rstrip('/')}/?data={encoded}"
    await message.answer(
        f"🎓 <b>Atestatsiya</b>\n\n"
        f"📊 Savollar: <b>{len(questions)} ta</b>\n"
        f"🔒 Tartib bo'yicha\n\n"
        f"Pastdagi tugmani bosib testni boshlang 👇",
        reply_markup=miniapp_keyboard(url),
        parse_mode="HTML"
    )

@router.message(F.text == "🏅 Milliy sertifikat")
async def milliy_menu(message: Message):
    if not await is_registered(message.from_user.id):
        await message.answer("❗ Avval ro'yxatdan o'ting — /start")
        return
    tid = message.from_user.id

    cnt = await count_questions(subject="milliy", category="milliy", is_attestation=True)
    if cnt == 0:
        await message.answer("❌ Milliy sertifikat savollari hali qo'shilmagan.")
        return

    # Oddiy to'lov tizimi — bepul 1 marta, keyin retry
    access_key = "milliy:milliy:None"
    status = await get_access_status(tid, access_key)

    if status == 'buy':
        from keyboards.keyboards import payment_options_keyboard
        await message.answer(
            "🏅 <b>Milliy sertifikat</b>\n\n"
            "📝 1-35: Variantli test\n"
            "✏️ 36-44: Yozma javob\n\n"
            "🔒 Birinchi bepul urinishingizni ishlatgansiz!\n"
            "Davom etish uchun to'lov turini tanlang:",
            reply_markup=payment_options_keyboard(access_key),
            parse_mode="HTML"
        )
        return

    if status == 'free':
        await mark_free_used(tid, access_key)

    await _launch_milliy_msg(message, tid)

async def _launch_milliy_msg(message: Message, tid: int):
    questions = await get_questions(
        subject="milliy", category="milliy",
        is_attestation=True, count=44
    )
    meta = {
        "subject": "milliy", "category": "milliy",
        "is_attestation": True, "solution_url": config.SOLUTION_URL
    }
    q_list  = questions_to_miniapp(questions)
    q_list  = await resolve_image_urls(q_list, message.bot)
    encoded = encode_questions(q_list, meta)
    url     = f"{config.MINI_APP_URL.rstrip('/')}/?data={encoded}"
    await message.answer(
        f"🏅 <b>Milliy sertifikat</b>\n\n"
        f"📝 Savollar: <b>{len(questions)} ta</b>\n"
        f"(1-35 variantli, 36-44 yozma)\n\n"
        f"Pastdagi tugmani bosib testni boshlang 👇",
        reply_markup=miniapp_keyboard(url),
        parse_mode="HTML"
    )

@router.message(F.text == "🎬 Videodarslar")
async def videodarslar_menu(message: Message):
    await message.answer(
        "🎬 <b>Videodarslar</b>\n\n⏳ Bu bo'lim tez orada ishga tushadi!",
        parse_mode="HTML"
    )

@router.message(F.text == "🎧 Audiolar")
async def audiolar_menu(message: Message):
    await message.answer(
        "🎧 <b>Audiolar</b>\n\n⏳ Bu bo'lim tez orada ishga tushadi!",
        parse_mode="HTML"
    )



# ══════════════════════════════════════════════
# BACK HANDLERS
# ══════════════════════════════════════════════

@router.callback_query(F.data == "back:main")
async def back_main(callback: CallbackQuery):
    await callback.message.delete()
    await callback.answer()

@router.callback_query(F.data == "back:onatili")
async def back_onatili(callback: CallbackQuery):
    await safe_edit(callback, "📚 <b>Ona tili</b>\n\nBo'limni tanlang:",
                    reply_markup=onatili_category_keyboard())
    await callback.answer()

@router.callback_query(F.data == "back:onatili:bolimlar")
async def back_onatili_bolimlar(callback: CallbackQuery):
    await safe_edit(callback, "📌 <b>Mavzulashtirilgan testlar</b>\n\nBo'limni tanlang:",
                    reply_markup=onatili_bolimlar_keyboard())
    await callback.answer()

@router.callback_query(F.data.startswith("back:onatili:bolim:"))
async def back_onatili_submavzu(callback: CallbackQuery):
    bolim = callback.data.split(":")[-1]
    label = config.ONA_TILI_BOLIMLAR.get(bolim, bolim)
    await safe_edit(callback,
        f"📌 <b>{label}</b>\n\nMavzuni tanlang:",
        reply_markup=onatili_submavzu_keyboard(bolim))
    await callback.answer()

@router.callback_query(F.data == "back:adabiyot")
async def back_adabiyot(callback: CallbackQuery):
    await safe_edit(callback, "📖 <b>Adabiyot</b>\n\nBo'limni tanlang:",
                    reply_markup=adabiyot_category_keyboard())
    await callback.answer()

@router.callback_query(F.data == "back:adabiyot:sinflar")
async def back_adabiyot_sinflar(callback: CallbackQuery):
    await safe_edit(callback, "🏫 <b>Sinfni tanlang:</b>",
                    reply_markup=grades_keyboard())
    await callback.answer()

@router.callback_query(F.data.startswith("back:adabiyot:grade:"))
async def back_adabiyot_boblar(callback: CallbackQuery):
    grade = callback.data.split(":")[-1]
    label = config.GRADES.get(grade, grade)
    await safe_edit(callback,
        f"🏫 <b>{label}</b>\n\nBobni tanlang:",
        reply_markup=adabiyot_boblar_keyboard(grade))
    await callback.answer()

@router.callback_query(F.data == "back:attestation")
async def back_attestation(callback: CallbackQuery):
    await callback.message.delete()
    await callback.answer()

# ══════════════════════════════════════════════
# ONA TILI
# ══════════════════════════════════════════════

@router.callback_query(F.data == "onatili:mavzu")
async def onatili_mavzu(callback: CallbackQuery):
    await safe_edit(callback,
        "📌 <b>Mavzulashtirilgan testlar</b>\n\nBo'limni tanlang:",
        reply_markup=onatili_bolimlar_keyboard())
    await callback.answer()

@router.callback_query(F.data == "onatili:aralash")
async def onatili_aralash(callback: CallbackQuery):
    await send_miniapp(callback, 'onatili', 'aralash')

# onatili:attestation — olib tashlandi, attestatsiya bitta

@router.callback_query(F.data.startswith("onatili:bolim:"))
async def onatili_bolim(callback: CallbackQuery):
    bolim = callback.data.split(":")[2]
    label = config.ONA_TILI_BOLIMLAR.get(bolim, bolim)
    submavzular = config.ONA_TILI_SUBMAVZULAR.get(bolim, {})
    if not submavzular:
        await send_miniapp(callback, 'onatili', 'mavzu', subcategory=bolim)
    else:
        await safe_edit(callback,
            f"📌 <b>{label}</b>\n\nMavzuni tanlang:",
            reply_markup=onatili_submavzu_keyboard(bolim))
        await callback.answer()

@router.callback_query(F.data.startswith("onatili:sub:"))
async def onatili_sub(callback: CallbackQuery):
    parts    = callback.data.split(":")
    bolim    = parts[2]
    submavzu = parts[3]
    if submavzu == '__aralash__':
        await send_miniapp(callback, 'onatili', 'mavzu', subcategory=bolim)
    else:
        await send_miniapp(callback, 'onatili', 'mavzu',
                           subcategory=f"{bolim}_{submavzu}")

# ══════════════════════════════════════════════
# ADABIYOT
# ══════════════════════════════════════════════

@router.callback_query(F.data == "adabiyot:sinf")
async def adabiyot_sinf(callback: CallbackQuery):
    await safe_edit(callback, "🏫 <b>Sinfni tanlang:</b>",
                    reply_markup=grades_keyboard())
    await callback.answer()

@router.callback_query(F.data == "adabiyot:aralash")
async def adabiyot_aralash(callback: CallbackQuery):
    await send_miniapp(callback, 'adabiyot', 'aralash')

@router.callback_query(F.data == "adabiyot:gazallar")
async def adabiyot_gazallar(callback: CallbackQuery):
    await send_miniapp(callback, 'adabiyot', 'gazallar')

@router.callback_query(F.data == "adabiyot:sheriy")
async def adabiyot_sheriy(callback: CallbackQuery):
    await send_miniapp(callback, 'adabiyot', 'sheriy')

@router.callback_query(F.data == "adabiyot:badiiy")
async def adabiyot_badiiy(callback: CallbackQuery):
    await send_miniapp(callback, 'adabiyot', 'badiiy')

# adabiyot:attestation — olib tashlandi, attestatsiya bitta

@router.callback_query(F.data.regexp(r"^adabiyot:grade:\d+$"))
async def adabiyot_grade(callback: CallbackQuery):
    grade = callback.data.split(":")[2]
    label = config.GRADES.get(grade, grade)
    await safe_edit(callback,
        f"🏫 <b>{label}</b>\n\nBobni tanlang:",
        reply_markup=adabiyot_boblar_keyboard(grade))
    await callback.answer()

@router.callback_query(F.data.regexp(r"^adabiyot:bob:\d+:\d+$"))
async def adabiyot_bob(callback: CallbackQuery):
    parts = callback.data.split(":")
    grade, bob = parts[2], parts[3]
    await send_miniapp(callback, 'adabiyot', 'sinf',
                       subcategory=f"{grade}_{bob}")

@router.callback_query(F.data.regexp(r"^adabiyot:grade_aralash:\d+$"))
async def adabiyot_grade_aralash(callback: CallbackQuery):
    grade = callback.data.split(":")[2]
    await send_miniapp(callback, 'adabiyot', 'sinf', subcategory=grade)

# ══════════════════════════════════════════════
# ATESTATSIYA FORMAT
# ══════════════════════════════════════════════

# attest_fmt endi ishlatilmaydi — attestatsiya bitta, fan ajratilmaydi

# ══════════════════════════════════════════════
# MINI APP NATIJA
# ══════════════════════════════════════════════

@router.message(F.web_app_data)
async def receive_miniapp_result(message: Message):
    from database.db import save_test_result
    try:
        data    = json.loads(message.web_app_data.data)
        correct = data.get('correct', 0)
        wrong   = data.get('wrong', 0)
        skipped = data.get('skip', 0)
        total   = data.get('total', 35)
        pct     = data.get('score', 0)

        tid = message.from_user.id
        await save_test_result(
            telegram_id=tid,
            subject=data.get('subject', 'onatili'),
            category=data.get('category', 'aralash'),
            subcategory=data.get('subcategory'),
            difficulty=None,
            correct=correct, wrong=wrong, skipped=skipped,
            is_attestation=data.get('is_attestation', False)
        )

        for qid in data.get('wrong_ids', []):
            try:
                await mark_wrong_question(tid, int(qid))
            except Exception:
                pass
        for qid in data.get('correct_ids', []):
            try:
                await mark_correct_question(tid, int(qid))
            except Exception:
                pass

        if pct >= 90:   grade, emoji = "A'lo (5)",      "🏆"
        elif pct >= 70: grade, emoji = "Yaxshi (4)",     "🎉"
        elif pct >= 50: grade, emoji = "Qoniqarli (3)",  "📚"
        else:           grade, emoji = "Qoniqarsiz (2)", "😔"

        user = message.from_user
        uname = f"@{user.username}" if user.username else user.full_name or str(tid)

        SUBJ = {'onatili': '📚 Ona tili', 'adabiyot': '📖 Adabiyot',
                'attestation': '🎓 Attestatsiya', 'milliy': '🏅 Milliy'}
        subj_label = SUBJ.get(data.get('subject',''), data.get('subject',''))

        result_text = (
            f"{emoji} <b>Test natijasi!</b>\n\n"
            f"━━━━━━━━━━━━━\n"
            f"✅ To'g'ri:    <b>{correct}/{total}</b>\n"
            f"❌ Xato:       <b>{wrong}/{total}</b>\n"
            f"⏭ O'tkazildi: <b>{skipped}</b>\n"
            f"📈 Ball:       <b>{pct}%</b>\n"
            f"🎓 Baho:       <b>{grade}</b>\n"
            f"━━━━━━━━━━━━━"
        )

        await message.answer(result_text, reply_markup=main_menu_keyboard())

        # Guruhga natija yuborish
        if config.RESULT_GROUP_ID:
            try:
                group_text = (
                    f"{emoji} <b>{uname}</b> — {subj_label}\n"
                    f"✅ {correct}/{total}  |  📈 {pct}%  |  🎓 {grade}"
                )
                await message.bot.send_message(
                    chat_id=config.RESULT_GROUP_ID,
                    text=group_text,
                    parse_mode="HTML"
                )
            except Exception:
                pass

    except Exception as e:
        await message.answer(f"❌ Xato: {e}")