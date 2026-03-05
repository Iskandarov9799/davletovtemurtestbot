from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.filters import CommandStart, Command

from database.db import get_user, create_user, update_user_phone, is_user_paid
from keyboards.keyboards import phone_keyboard, main_menu_keyboard
from states import RegistrationStates
from config import config

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    """Bot boshlanishi"""
    await state.clear()

    user = get_user(message.from_user.id)

    if not user:
        create_user(
            telegram_id=message.from_user.id,
            full_name=message.from_user.full_name,
            username=message.from_user.username
        )

    user = get_user(message.from_user.id)

    if user and user['is_registered']:
        paid = is_user_paid(message.from_user.id)
        await message.answer(
            f"👋 Xush kelibsiz, <b>{message.from_user.full_name}</b>!\n\n"
            f"{'✅ To\'lovingiz tasdiqlangan!' if paid else '⏳ To\'lovingizni amalga oshiring.'}",
            reply_markup=main_menu_keyboard(is_paid=paid),
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

@router.message(RegistrationStates.waiting_for_phone, F.contact)
async def process_phone(message: Message, state: FSMContext):
    """Telefon raqamini qabul qilish"""
    contact = message.contact

    # Faqat o'z raqamini ulashishga ruxsat
    if contact.user_id != message.from_user.id:
        await message.answer("❌ Faqat o'z telefon raqamingizni ulashishingiz mumkin!")
        return

    phone = contact.phone_number
    if not phone.startswith('+'):
        phone = '+' + phone

    update_user_phone(telegram_id=message.from_user.id, phone=phone)

    await state.clear()

    await message.answer(
        f"✅ <b>Muvaffaqiyatli ro'yxatdan o'tdingiz!</b>\n\n"
        f"👤 Ism: {message.from_user.full_name}\n"
        f"📱 Telefon: {phone}\n\n"
        f"💳 Test ishlatish uchun to'lov qilishingiz kerak.\n"
        f"Narxi: <b>{config.PAYMENT_AMOUNT:,} so'm</b>\n\n"
        f"\"💳 To'lov qilish\" tugmasini bosing:",
        reply_markup=main_menu_keyboard(is_paid=False),
        parse_mode="HTML"
    )

@router.message(RegistrationStates.waiting_for_phone)
async def wrong_contact(message: Message):
    """Noto'g'ri formatda javob"""
    await message.answer(
        "📱 Iltimos, quyidagi tugmani bosib telefon raqamingizni ulashing:",
        reply_markup=phone_keyboard()
    )

@router.message(Command("admin"))
async def admin_panel(message: Message):
    """Admin paneli"""
    if message.from_user.id not in config.ADMIN_IDS:
        await message.answer("⛔ Siz admin emassiz!")
        return

    from keyboards.keyboards import admin_keyboard
    await message.answer(
        "🔐 <b>Admin panel</b>\n\nQuyidagi amallardan birini tanlang:",
        reply_markup=admin_keyboard(),
        parse_mode="HTML"
    )

@router.message(F.text == "ℹ️ Ma'lumot")
async def info_handler(message: Message):
    """Ma'lumot"""
    await message.answer(
        "📚 <b>Ona tili va Adabiyot Test Boti</b>\n\n"
        "🎯 <b>Qanday ishlaydi?</b>\n"
        "1️⃣ Telefon raqamingizni ulashing\n"
        "2️⃣ To'lov qiling va chekni yuboring\n"
        "3️⃣ Admin tasdiqlaydi\n"
        "4️⃣ 30 ta random savol ishlang\n"
        "5️⃣ Natijangizni ko'ring!\n\n"
        f"💰 <b>Narxi:</b> {config.PAYMENT_AMOUNT:,} so'm\n\n"
        "📞 <b>Muammo bo'lsa:</b> @admin_username",
        parse_mode="HTML"
    )