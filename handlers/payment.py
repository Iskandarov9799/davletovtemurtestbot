from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from database.db import (
    get_user, create_payment, confirm_payment, reject_payment,
    get_pending_payments, is_user_paid, is_user_registered
)
from keyboards.keyboards import (
    cancel_keyboard, main_menu_keyboard, payment_confirm_keyboard
)
from states import PaymentStates
from config import config

router = Router()

@router.message(F.text == "💳 To'lov qilish")
async def payment_info(message: Message, state: FSMContext):
    """To'lov ma'lumotlari"""

    if not is_user_registered(message.from_user.id):
        await message.answer("❌ Avval ro'yxatdan o'ting! /start")
        return

    if is_user_paid(message.from_user.id):
        await message.answer(
            "✅ Siz allaqachon to'lov qilgansiz!\n"
            "📝 Testni boshlashingiz mumkin.",
            reply_markup=main_menu_keyboard(is_paid=True)
        )
        return

    await message.answer(
        f"💳 <b>To'lov ma'lumotlari</b>\n\n"
        f"💰 Summa: <b>{config.PAYMENT_AMOUNT:,} so'm</b>\n\n"
        f"🏦 Karta raqami:\n"
        f"<code>{config.PAYMENT_CARD_NUMBER}</code>\n\n"
        f"👤 Karta egasi: <b>{config.PAYMENT_CARD_OWNER}</b>\n\n"
        f"📸 To'lovni amalga oshirgach, <b>to'lov chekining rasmini</b> yuboring.\n\n"
        f"⚠️ Izoh: To'lov 5-30 daqiqa ichida tasdiqlanadi.",
        parse_mode="HTML",
        reply_markup=cancel_keyboard()
    )
    await state.set_state(PaymentStates.waiting_for_check)

@router.message(PaymentStates.waiting_for_check, F.photo)
async def receive_payment_check(message: Message, state: FSMContext, bot: Bot):
    """Chek rasmini qabul qilish"""

    photo_id = message.photo[-1].file_id
    user = get_user(message.from_user.id)

    # Save payment to DB
    payment_id = create_payment(
        telegram_id=message.from_user.id,
        check_photo_id=photo_id
    )

    await message.answer(
        "✅ <b>To'lov cheki qabul qilindi!</b>\n\n"
        "⏳ Admin tekshirib, tasdiqlaydi.\n"
        "🔔 Tasdiqlangandan so'ng sizga xabar keladi.\n\n"
        "Odatda 5-30 daqiqa davom etadi.",
        parse_mode="HTML",
        reply_markup=main_menu_keyboard(is_paid=False)
    )

    await state.clear()

    # Send to all admins
    for admin_id in config.ADMIN_IDS:
        try:
            await bot.send_photo(
                chat_id=admin_id,
                photo=photo_id,
                caption=(
                    f"💰 <b>Yangi to'lov cheki!</b>\n\n"
                    f"👤 Foydalanuvchi: {message.from_user.full_name}\n"
                    f"🆔 ID: <code>{message.from_user.id}</code>\n"
                    f"📱 Telefon: {user['phone_number'] if user else 'Noma\'lum'}\n"
                    f"🔗 Username: @{message.from_user.username or 'yo\'q'}\n"
                    f"💵 Summa: {config.PAYMENT_AMOUNT:,} so'm\n\n"
                    f"✅ Tasdiqlash yoki ❌ Rad etish:"
                ),
                reply_markup=payment_confirm_keyboard(message.from_user.id),
                parse_mode="HTML"
            )
        except Exception as e:
            print(f"Admin ga xabar yuborishda xato: {e}")

@router.message(PaymentStates.waiting_for_check, F.text == "❌ Bekor qilish")
async def cancel_payment(message: Message, state: FSMContext):
    """To'lovni bekor qilish"""
    await state.clear()
    paid = is_user_paid(message.from_user.id)
    await message.answer(
        "❌ Bekor qilindi.",
        reply_markup=main_menu_keyboard(is_paid=paid)
    )

@router.message(PaymentStates.waiting_for_check)
async def wrong_payment_format(message: Message):
    """Noto'g'ri format"""
    await message.answer(
        "📸 Iltimos, to'lov chekining <b>rasmini</b> yuboring!\n"
        "(Rasmni kamera yoki gallereyadan tanlang)",
        parse_mode="HTML"
    )

# ============ ADMIN CALLBACKS ============

@router.callback_query(F.data.startswith("confirm_pay:"))
async def confirm_payment_callback(callback: CallbackQuery, bot: Bot):
    """Adminning to'lovni tasdiqlashi"""

    if callback.from_user.id not in config.ADMIN_IDS:
        await callback.answer("⛔ Ruxsat yo'q!", show_alert=True)
        return

    user_telegram_id = int(callback.data.split(":")[1])

    confirm_payment(
        telegram_id=user_telegram_id,
        admin_id=callback.from_user.id
    )

    # Edit admin message
    await callback.message.edit_caption(
        caption=callback.message.caption + f"\n\n✅ <b>TASDIQLANDI</b> - Admin: {callback.from_user.full_name}",
        parse_mode="HTML"
    )

    # Notify user
    try:
        await bot.send_message(
            chat_id=user_telegram_id,
            text=(
                "🎉 <b>Tabriklaymiz! To'lovingiz tasdiqlandi!</b>\n\n"
                "✅ Endi testni boshlashingiz mumkin!\n"
                "📝 Testni boshlash uchun \"📝 Testni boshlash\" tugmasini bosing."
            ),
            reply_markup=main_menu_keyboard(is_paid=True),
            parse_mode="HTML"
        )
    except Exception as e:
        print(f"Foydalanuvchiga xabar yuborishda xato: {e}")

    await callback.answer("✅ To'lov tasdiqlandi!", show_alert=True)

@router.callback_query(F.data.startswith("reject_pay:"))
async def reject_payment_callback(callback: CallbackQuery, bot: Bot):
    """Adminning to'lovni rad etishi"""

    if callback.from_user.id not in config.ADMIN_IDS:
        await callback.answer("⛔ Ruxsat yo'q!", show_alert=True)
        return

    user_telegram_id = int(callback.data.split(":")[1])

    reject_payment(
        telegram_id=user_telegram_id,
        admin_id=callback.from_user.id
    )

    await callback.message.edit_caption(
        caption=callback.message.caption + f"\n\n❌ <b>RAD ETILDI</b> - Admin: {callback.from_user.full_name}",
        parse_mode="HTML"
    )

    # Notify user
    try:
        await bot.send_message(
            chat_id=user_telegram_id,
            text=(
                "❌ <b>To'lovingiz rad etildi.</b>\n\n"
                "Sabab: To'lov cheki noto'g'ri yoki summa mos emas.\n\n"
                "💳 Qayta to'lov qilishingiz mumkin.\n"
                f"Karta: <code>{config.PAYMENT_CARD_NUMBER}</code>"
            ),
            reply_markup=main_menu_keyboard(is_paid=False),
            parse_mode="HTML"
        )
    except Exception as e:
        print(f"Foydalanuvchiga xabar yuborishda xato: {e}")

    await callback.answer("❌ To'lov rad etildi!", show_alert=True)

# ============ ADMIN TEXT HANDLERS ============

@router.message(F.text == "💰 Kutayotgan to'lovlar")
async def pending_payments_handler(message: Message):
    """Kutayotgan to'lovlar ro'yxati"""
    if message.from_user.id not in config.ADMIN_IDS:
        return

    payments = get_pending_payments()

    if not payments:
        await message.answer("✅ Kutayotgan to'lovlar yo'q!")
        return

    await message.answer(f"💰 <b>Kutayotgan to'lovlar: {len(payments)} ta</b>", parse_mode="HTML")

    for pay in payments:
        await message.answer(
            f"👤 {pay['full_name']}\n"
            f"📱 {pay['phone_number']}\n"
            f"🆔 {pay['telegram_id']}\n"
            f"📅 {pay['submitted_at'][:16]}",
            parse_mode="HTML"
        )