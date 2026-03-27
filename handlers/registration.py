from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.filters import CommandStart, Command

from database.db import (
    get_user, create_user, update_user_phone,
    is_registered, get_user_results, get_leaderboard
)
from keyboards.keyboards import (
    phone_keyboard, main_menu_keyboard,
    cancel_keyboard, admin_keyboard
)
from states import RegistrationStates
from config import config

router = Router()

# ══════════════════════════════════════════════
# /start
# ══════════════════════════════════════════════

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()

    user = await get_user(message.from_user.id)

    if not user:
        await create_user(
            telegram_id=message.from_user.id,
            full_name=message.from_user.full_name,
            username=message.from_user.username
        )
        user = await get_user(message.from_user.id)

    if user and user.is_registered:
        await message.answer(
            f"👋 Xush kelibsiz, <b>{message.from_user.full_name}</b>!\n\n"
            f"📚 Fan tanlang va testni boshlang:",
            reply_markup=main_menu_keyboard(),
            parse_mode="HTML"
        )
    else:
        await message.answer(
            "👋 <b>Ona tili va Adabiyot Test Botiga xush kelibsiz!</b>\n\n"
            "📋 Ro'yxatdan o'tish uchun telefon raqamingizni ulashing.\n\n"
            "⬇️ Quyidagi tugmani bosing:",
            reply_markup=phone_keyboard(),
            parse_mode="HTML"
        )
        await state.set_state(RegistrationStates.waiting_for_phone)

# ══════════════════════════════════════════════
# Telefon qabul qilish
# ══════════════════════════════════════════════

@router.message(RegistrationStates.waiting_for_phone, F.contact)
async def process_phone(message: Message, state: FSMContext):
    contact = message.contact

    if contact.user_id != message.from_user.id:
        await message.answer("❌ Faqat o'z telefon raqamingizni ulashishingiz mumkin!")
        return

    phone = contact.phone_number
    if not phone.startswith('+'):
        phone = '+' + phone

    await update_user_phone(telegram_id=message.from_user.id, phone=phone)
    await state.clear()

    await message.answer(
        f"✅ <b>Muvaffaqiyatli ro'yxatdan o'tdingiz!</b>\n\n"
        f"👤 Ism: <b>{message.from_user.full_name}</b>\n"
        f"📱 Telefon: <b>{phone}</b>\n\n"
        f"📚 Endi fan tanlang va testni boshlang.\n"
        f"🎯 Birinchi urinish <b>bepul</b>!",
        reply_markup=main_menu_keyboard(),
        parse_mode="HTML"
    )

@router.message(RegistrationStates.waiting_for_phone)
async def wrong_contact(message: Message):
    await message.answer(
        "📱 Iltimos, quyidagi tugmani bosib telefon raqamingizni ulashing:",
        reply_markup=phone_keyboard()
    )

# ══════════════════════════════════════════════
# Asosiy menyu tugmalari
# ══════════════════════════════════════════════
# ESLATMA: 📚 Ona tili, 📖 Adabiyot, 🎓 Atestatsiya handlerlari
# test_handler.py da to'liq ro'yxatdan o'tgan — bu yerda TAKRORLANMAYDI.

@router.message(F.text == "📊 Natijalarim")
async def menu_results(message: Message):
    if not await is_registered(message.from_user.id):
        await message.answer("❌ Avval ro'yxatdan o'ting! /start")
        return

    results = await get_user_results(message.from_user.id, limit=10)
    if not results:
        await message.answer(
            "📊 Hali test ishlamagansiz.\n"
            "📚 Ona tili yoki Adabiyotdan boshlang!"
        )
        return

    SUBJ = {'onatili': '📚 Ona tili', 'adabiyot': '📖 Adabiyot'}
    DIFF = {'easy': '🟢', 'medium': '🟡', 'hard': '🔴'}

    text = "📊 <b>So'nggi natijalaringiz:</b>\n\n"
    for i, r in enumerate(results, 1):
        subj  = SUBJ.get(r.subject, r.subject or '')
        diff  = DIFF.get(r.difficulty, '') if r.difficulty else ''
        date  = str(r.finished_at)[:10] if r.finished_at else '—'
        sub   = f" › {r.subcategory}" if r.subcategory else ''
        text += (
            f"{i}. {subj} {diff}\n"
            f"   📁 {r.category or ''}{sub}\n"
            f"   ✅ {r.correct}/{r.total}  📈 {r.score}%\n"
            f"   📅 {date}  (#{r.attempt_number} urinish)\n\n"
        )
    await message.answer(text, parse_mode="HTML")

@router.message(F.text == "🏆 Reyting")
async def menu_leaderboard(message: Message):
    leaders = await get_leaderboard(10)
    if not leaders:
        await message.answer("🏆 Hali reyting mavjud emas!")
        return

    medals = ["🥇","🥈","🥉","4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣","🔟"]
    text = "🏆 <b>Eng yaxshi natijalar:</b>\n\n"
    for i, row in enumerate(leaders):
        medal = medals[i] if i < len(medals) else f"{i+1}."
        name  = row.full_name or "Noma'lum"
        text += f"{medal} <b>{name}</b> — {row.best_score}%  ({row.attempts} marta)\n"
    await message.answer(text, parse_mode="HTML")

@router.message(F.text == "👤 Profil")
async def menu_profile(message: Message):
    user = await get_user(message.from_user.id)
    if not user:
        await message.answer("❌ Avval ro'yxatdan o'ting! /start")
        return

    results = await get_user_results(message.from_user.id)
    total_tests = len(results)
    best_score  = max((r.score for r in results), default=0)
    reg_date    = str(user.registered_at)[:10] if user.registered_at else '—'

    await message.answer(
        f"👤 <b>Profil</b>\n\n"
        f"📛 Ism: <b>{user.full_name}</b>\n"
        f"📱 Telefon: <b>{user.phone_number or '—'}</b>\n"
        f"📅 Ro'yxat: <b>{reg_date}</b>\n\n"
        f"📊 Jami testlar: <b>{total_tests}</b>\n"
        f"🏆 Eng yaxshi natija: <b>{best_score}%</b>",
        parse_mode="HTML"
    )

@router.message(F.text == "ℹ️ Yordam")
async def menu_help(message: Message):
    text = (
        "📚 <b>Ona tili va Adabiyot Test Boti</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        "📚 <b>ONA TILI</b>\n"
        "• Mavzulashtirilgan — bo'lim va mavzu tanlang\n"
        "• Aralash — barcha mavzulardan aralash test\n"
        f"🎯 Birinchi urinish <b>bepul</b>, keyingisi {config.PRICE_ONCE:,} so'm\n"
        f"📅 Kunlik obuna — {config.PRICE_DAILY:,} so'm (24 soat)\n"
        f"📆 Oylik obuna — {config.PRICE_MONTHLY:,} so'm (30 kun)\n\n"
        "📖 <b>ADABIYOT</b>\n"
        "• Sinflar bo'yicha (5-11 sinf, boblar)\n"
        "• Aralash, G'azallar, She'riy san'atlar\n"
        f"🎯 Birinchi urinish <b>bepul</b>, keyingisi {config.PRICE_ONCE:,} so'm\n"
        f"📅 Kunlik obuna — {config.PRICE_DAILY:,} so'm (24 soat)\n"
        f"📆 Oylik obuna — {config.PRICE_MONTHLY:,} so'm (30 kun)\n\n"
        "🎓 <b>ATESTATSIYA</b>\n"
        "• 10 ta bo'lim, har birida 35 ta savol\n"
        "1️⃣ Bo'limni tanlang\n"
        f"2️⃣ To'lov — bir martalik <b>{config.PRICE_ATTESTATION:,} so'm</b>\n"
        "3️⃣ To'lov qilingan bo'lim ochiladi\n\n"
        "💳 <b>TO'LOV TARTIBI</b>\n"
        "1️⃣ Bo'limni tanlang\n"
        "2️⃣ Sotib olish tugmasini bosing\n"
        "3️⃣ Karta raqamiga pul o'tkazing\n"
        "4️⃣ Chek rasmini botga yuboring\n"
        "5️⃣ Admin tasdiqlaydi — test ochiladi\n\n"
        "📊 <b>BOSHQA IMKONIYATLAR</b>\n"
        "• 📊 Natijalarim — oxirgi 10 ta test natijasi\n"
        "• 🏆 Reyting — eng yaxshi natijalar\n"
        "• 👤 Profil — shaxsiy ma'lumotlar\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "❓ Muammo bo'lsa adminga yozing"
    )
    await message.answer(text, parse_mode="HTML")


# ══════════════════════════════════════════════
# Admin
# ══════════════════════════════════════════════

@router.message(Command("admin"))
async def cmd_admin(message: Message):
    if message.from_user.id not in config.ADMIN_IDS:
        await message.answer("⛔ Siz admin emassiz!")
        return
    await message.answer(
        "🔐 <b>Admin panel</b>",
        reply_markup=admin_keyboard(),
        parse_mode="HTML"
    )

@router.message(F.text == "🔙 Orqaga")
async def back_to_main(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "🏠 Asosiy menyu:",
        reply_markup=main_menu_keyboard()
    )