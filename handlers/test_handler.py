import json, base64, zlib, logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

from database.db import (
    is_registered, get_access_status, mark_free_used, mark_once_used,
    has_attestation,
    get_questions, count_questions,
    mark_wrong_question, mark_correct_question
)
from keyboards.keyboards import (
    onatili_category_keyboard, onatili_bolimlar_keyboard,
    onatili_submavzu_keyboard, adabiyot_category_keyboard,
    adabiyot_boblar_keyboard, grades_keyboard,
    payment_options_keyboard, attestation_buy_standalone_keyboard,
    attestation_bolimlar_keyboard,
    main_menu_keyboard
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
    return [{
        "id":    q.id,
        "t":     q.question_text,
        "a":     q.option_a,
        "b":     q.option_b,
        "c":     q.option_c,
        "d":     q.option_d,
        "ok":    q.correct_answer,
        "img":   q.image_file_id or "",
        "type":  getattr(q, 'question_type', 'choice'),
        "parts": getattr(q, 'written_parts', 1),
        "kw1":   getattr(q, 'keywords_1', None) or "",
        "kw2":   getattr(q, 'keywords_2', None) or "",
    } for q in questions]

async def resolve_image_urls(q_list: list, bot) -> list:
    result = []
    for q in q_list:
        img = q.get("img", "")
        if not img:
            result.append(q); continue
        if img.startswith("http"):
            result.append(q); continue
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
            try:
                file = await bot.get_file(img)
                url = f"https://api.telegram.org/file/bot{bot.token}/{file.file_path}"
                q = {**q, "img": url}
            except Exception:
                q = {**q, "img": ""}
        result.append(q)
    return result

_image_url_cache: dict = {}

async def upload_to_cloudinary(file_id: str, bot, config) -> str:
    import aiohttp, io, hashlib, hmac, time
    if file_id in _image_url_cache:
        return _image_url_cache[file_id]
    file   = await bot.get_file(file_id)
    tg_url = f"https://api.telegram.org/file/bot{bot.token}/{file.file_path}"
    async with aiohttp.ClientSession() as session:
        async with session.get(tg_url) as resp:
            img_bytes = await resp.read()
        timestamp = str(int(time.time()))
        public_id = f"bot_imgs/{file_id[:20]}"
        sign_str  = f"public_id={public_id}&timestamp={timestamp}"
        signature = hmac.new(
            config.CLOUDINARY_API_SECRET.encode(),
            sign_str.encode(), hashlib.sha1
        ).hexdigest()
        form = aiohttp.FormData()
        form.add_field('file',      img_bytes,               content_type='image/jpeg')
        form.add_field('api_key',   config.CLOUDINARY_API_KEY)
        form.add_field('timestamp', timestamp)
        form.add_field('public_id', public_id)
        form.add_field('signature', signature)
        upload_url = f"https://api.cloudinary.com/v1_1/{config.CLOUDINARY_CLOUD_NAME}/image/upload"
        async with session.post(upload_url, data=form) as resp:
            data = await resp.json()
            if 'secure_url' not in data:
                raise Exception(f"Cloudinary javob: {data}")
            url = data['secure_url']
    _image_url_cache[file_id] = url
    return url


def test_link_keyboard(url: str, label: str = "🚀 Testni boshlash"):
    """Test havolasini Mini App sifatida ochish"""
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=label, web_app=WebAppInfo(url=url))
    ]])


async def safe_edit(callback, text, reply_markup=None):
    from aiogram.types import ReplyKeyboardMarkup
    try:
        if isinstance(reply_markup, ReplyKeyboardMarkup):
            try:
                await callback.message.edit_text(text, reply_markup=None, parse_mode="HTML")
            except Exception:
                pass
            await callback.message.answer("👇", reply_markup=reply_markup)
        else:
            await callback.message.edit_text(text, reply_markup=reply_markup, parse_mode="HTML")
    except Exception as e:
        if "message is not modified" not in str(e):
            pass


async def send_miniapp(callback, subject, category,
                       subcategory=None, is_attestation=False):
    SUBJ = {
        'onatili':     '📚 Ona tili',
        'adabiyot':    '📖 Adabiyot',
        'attestation': '🎓 Attestatsiya',
        'milliy':      '🏅 Milliy sertifikat',
    }
    tid = callback.from_user.id
    bot = callback.bot

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

    questions = await get_questions(
        subject=subject, category=category,
        subcategory=subcategory, difficulty=None,
        count=config.ATTESTATION_COUNT if is_attestation else min(cnt, config.MAX_QUESTIONS),
        is_attestation=is_attestation,
        telegram_id=tid if not is_attestation else None
    )

    meta = {
        'subject': subject, 'category': category, 'subcategory': subcategory,
        'is_attestation': is_attestation, 'solution_url': config.SOLUTION_URL
    }
    q_list  = questions_to_miniapp(questions)
    q_list  = await resolve_image_urls(q_list, bot)
    encoded = encode_questions(q_list, meta)
    url     = f"{config.MINI_APP_URL.rstrip('/')}/?data={encoded}"

    # Chiroyli nom
    if subcategory:
        parts_sub = subcategory.split('_', 1)
        if len(parts_sub) == 2:
            grade_key, bob_key = parts_sub
            grade_name = config.GRADES.get(grade_key, grade_key)
            bob_name   = config.ADABIYOT_BOBLAR.get(grade_key, {}).get(bob_key, f"{bob_key}-bob")
            sub_label  = f" › {grade_name} › {bob_name}"
        else:
            sub_label = f" › {config.GRADES.get(subcategory, subcategory)}"
    else:
        sub_label = ''

    subj_text = SUBJ.get(subject, subject)
    await safe_edit(callback,
        f"<b>{subj_text}{sub_label}</b>\n\n"
        f"📊 Savollar: <b>{len(questions)} ta</b>\n"
        f"{'🔒 Tartib bo\'yicha' if is_attestation else '🎲 Random tartibda'}\n\n"
        f"Quyidagi tugmani bosib testni boshlang 👇",
        reply_markup=test_link_keyboard(url)
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

    # Har doim bo'limlar ko'rsatiladi — to'lov bo'lim tanlangandan keyin so'raladi
    paid = await has_attestation(tid, "attestation")
    status_text = "" if paid else f"\n💳 Narxi: <b>{config.PRICE_ATTESTATION:,} so'm</b> (bir martalik)"
    await message.answer(
        f"🎓 <b>Atestatsiya</b>\n"
        f"📋 Har bir bo'limda 35 ta savol{status_text}\n\n"
        f"Bo'limni tanlang:",
        reply_markup=attestation_bolimlar_keyboard(),
        parse_mode="HTML"
    )

async def _launch_attestation_bolim(message_or_callback, tid: int,
                                     bolim_num: int, is_callback: bool = False):
    """Attestatsiya bo'limini ishga tushirish"""
    subcategory = f"bolim_{bolim_num}"
    questions = await get_questions(
        subject="attestation", category="attestation",
        subcategory=subcategory,
        is_attestation=True, count=config.ATTESTATION_COUNT
    )
    if not questions:
        # Bo'limda savol yo'q — umumiy savollardan olish
        questions = await get_questions(
            subject="attestation", category="attestation",
            is_attestation=True, count=config.ATTESTATION_COUNT
        )

    meta = {
        "subject": "attestation", "category": "attestation",
        "subcategory": subcategory,
        "is_attestation": True, "solution_url": config.SOLUTION_URL
    }
    q_list  = questions_to_miniapp(questions)
    if is_callback:
        q_list = await resolve_image_urls(q_list, message_or_callback.bot)
    else:
        q_list = await resolve_image_urls(q_list, message_or_callback.bot)

    encoded = encode_questions(q_list, meta)
    url     = f"{config.MINI_APP_URL.rstrip('/')}/?data={encoded}"

    text = (
        f"🎓 <b>Atestatsiya — {bolim_num}-bo'lim</b>\n\n"
        f"📊 Savollar: <b>{len(questions)} ta</b>\n"
        f"🔒 Tartib bo'yicha\n\n"
        f"Quyidagi tugmani bosib testni boshlang 👇"
    )
    kb = test_link_keyboard(url, f"🚀 {bolim_num}-bo'lim testini boshlash")

    if is_callback:
        await safe_edit(message_or_callback, text, reply_markup=kb)
        await message_or_callback.answer()
    else:
        await message_or_callback.answer(text, reply_markup=kb, parse_mode="HTML")


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

    access_key = "milliy:milliy:None"
    status = await get_access_status(tid, access_key)

    if status == 'buy':
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
        f"Quyidagi tugmani bosib testni boshlang 👇",
        reply_markup=test_link_keyboard(url),
        parse_mode="HTML"
    )

@router.message(F.text == "🎬 Videodarslar")
async def videodarslar_menu(message: Message):
    await message.answer("🎬 <b>Videodarslar</b>\n\n⏳ Bu bo'lim tez orada ishga tushadi!", parse_mode="HTML")

@router.message(F.text == "🎧 Audiolar")
async def audiolar_menu(message: Message):
    await message.answer("🎧 <b>Audiolar</b>\n\n⏳ Bu bo'lim tez orada ishga tushadi!", parse_mode="HTML")


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
    await safe_edit(callback,
        "🎓 <b>Atestatsiya</b>\n\nBo'limni tanlang:",
        reply_markup=attestation_bolimlar_keyboard())
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
# ATTESTATSIYA BO'LIMLARI (10 ta)
# ══════════════════════════════════════════════

@router.callback_query(F.data.startswith("attest:bolim:"))
async def attestation_bolim(callback: CallbackQuery):
    bolim_num = int(callback.data.split(":")[2])
    tid       = callback.from_user.id

    # Sotib olinmagan bo'lsa — bu bo'lim uchun to'lov so'ra
    if not await has_attestation(tid, "attestation"):
        await safe_edit(callback,
            f"🎓 <b>Atestatsiya — {bolim_num}-bo'lim</b>\n\n"
            f"📋 35 ta savol | Bir martalik to'lov\n"
            f"💰 Narxi: <b>{config.PRICE_ATTESTATION:,} so'm</b>\n\n"
            f"To'lov qilganingizdan so'ng <b>barcha 10 bo'lim</b> ochiladi.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text=f"💳 Sotib olish — {config.PRICE_ATTESTATION:,} so'm",
                    callback_data="buy:attestation"
                )],
                [InlineKeyboardButton(
                    text="🔙 Orqaga",
                    callback_data="back:attestation"
                )],
            ])
        )
        await callback.answer()
        return

    await _launch_attestation_bolim(callback, tid, bolim_num, is_callback=True)

# web_app_data handler miniapp_handler.py da