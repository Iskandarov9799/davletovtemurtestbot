"""
To'lov tizimi:
  daily       — 10,000 so'm (24 soat barcha testlar)
  monthly     — 100,000 so'm (30 kun barcha testlar)
  attestation — 5,000 so'm (bir martalik atestatsiya bo'limi)
"""
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from database.db import (
    create_purchase, confirm_purchase, reject_purchase,
    get_purchase_by_id, get_pending_purchases,
    grant_subscription, grant_attestation, get_user,
    get_questions, count_questions
)
from keyboards.keyboards import (
    cancel_keyboard, payment_confirm_keyboard,
    main_menu_keyboard, attestation_bolimlar_keyboard
)
from handlers.test_handler import (
    questions_to_miniapp, encode_questions,
    resolve_image_urls, make_test_keyboard
)
from states import PaymentStates
from config import config

router = Router()

PRODUCT_PRICES = {
    'daily':   config.PRICE_DAILY,
    'monthly': config.PRICE_MONTHLY,
    'milliy':  getattr(config, 'PRICE_MILLIY', 50_000),
}
PRODUCT_LABELS = {
    'daily':   f"Kunlik — {config.PRICE_DAILY:,} so'm",
    'monthly': f"Oylik — {config.PRICE_MONTHLY:,} so'm",
    'milliy':  f"Milliy sertifikat — {getattr(config, 'PRICE_MILLIY', 50_000):,} so'm",
}

# ── TO'LOV BOSHLASH ────────────────────────────────

@router.callback_query(F.data.startswith("pay:"))
async def pay_start(callback: CallbackQuery, state: FSMContext):
    parts    = callback.data.split(":", 2)
    pay_type = parts[1]
    key      = parts[2] if len(parts) > 2 else ''

    amount = PRODUCT_PRICES.get(pay_type, 0)
    label  = PRODUCT_LABELS.get(pay_type, '')

    await state.update_data(product_type=pay_type, retry_key=key, amount=amount)
    await callback.message.edit_text(
        f"💳 <b>{label}</b>\n\n"
        f"To'lov miqdori: <b>{amount:,} so'm</b>\n\n"
        f"Kartaga o'tkazing:\n"
        f"<code>{config.PAYMENT_CARD}</code>\n"
        f"<b>{config.PAYMENT_OWNER}</b>\n\n"
        f"To'lovni amalga oshirgandan so'ng <b>chek rasmini</b> yuboring 👇",
        reply_markup=cancel_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(PaymentStates.waiting_for_check)
    await callback.answer()


@router.callback_query(F.data.startswith("buy:attest_bolim:"))
async def attestation_bolim_pay(callback: CallbackQuery, state: FSMContext):
    bolim_num = callback.data.split(":")[2]
    amount    = config.PRICE_ATTESTATION
    # retry_key sifatida bo'lim nomini saqlaymiz
    bolim_key = f"bolim_{bolim_num}"
    await state.update_data(
        product_type='attestation',
        retry_key=bolim_key,
        amount=amount
    )
    await callback.message.edit_text(
        f"🎓 <b>Atestatsiya — {bolim_num}-bo'lim</b>\n\n"
        f"💰 To'lov miqdori: <b>{amount:,} so'm</b>\n\n"
        f"Kartaga o'tkazing:\n"
        f"<code>{config.PAYMENT_CARD}</code>\n"
        f"<b>{config.PAYMENT_OWNER}</b>\n\n"
        f"Chek rasmini yuboring 👇",
        reply_markup=cancel_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(PaymentStates.waiting_for_check)
    await callback.answer()


# ── CHEK QABUL QILISH ─────────────────────────────

@router.message(PaymentStates.waiting_for_check, F.photo)
async def receive_check(message: Message, state: FSMContext, bot: Bot):
    data         = await state.get_data()
    product_type = data.get('product_type')
    retry_key    = data.get('retry_key')
    amount       = data.get('amount', 0)
    await state.clear()

    file_id     = message.photo[-1].file_id
    purchase_id = await create_purchase(
        telegram_id  = message.from_user.id,
        product_type = product_type,
        amount       = amount,
        check_photo  = file_id,
        retry_key    = retry_key
    )

    await message.answer(
        "✅ <b>Chekingiz qabul qilindi!</b>\n\n"
        "⏳ Admin tekshirib, tez orada aktivlashtiradi.",
        reply_markup=main_menu_keyboard(),
        parse_mode="HTML"
    )

    user = await get_user(message.from_user.id)
    uname = f"@{user.username}" if user and user.username else str(message.from_user.id)
    LABELS = {
        'daily': 'Kunlik',
        'monthly': 'Oylik', 'attestation': 'Atestatsiya',
    }
    label    = LABELS.get(product_type, product_type)
    key_info = f"\n🔑 Key: <code>{retry_key}</code>" if retry_key else ""

    for admin_id in config.ADMIN_IDS:
        try:
            await bot.send_photo(
                chat_id      = admin_id,
                photo        = file_id,
                caption      = (
                    f"💰 <b>Yangi to'lov #{purchase_id}</b>\n\n"
                    f"👤 {user.full_name if user else '?'} | {uname}\n"
                    f"📦 Turi: <b>{label}</b>{key_info}\n"
                    f"💵 Summa: <b>{amount:,} so'm</b>"
                ),
                reply_markup = payment_confirm_keyboard(purchase_id),
                parse_mode   = "HTML"
            )
        except Exception:
            pass


@router.message(PaymentStates.waiting_for_check)
async def check_not_photo(message: Message):
    if message.text and "Bekor" in message.text:
        return
    await message.answer(
        "📸 Iltimos, <b>rasm</b> (chek screenshot) yuboring.",
        parse_mode="HTML"
    )


@router.callback_query(F.data == "payment:cancel")
async def payment_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    # edit_text faqat InlineKeyboardMarkup qabul qiladi
    # Shuning uchun: avval inline olib tashlaymiz, keyin ReplyKeyboard yuboramiz
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    await callback.message.answer("❌ Bekor qilindi.", reply_markup=main_menu_keyboard())
    await callback.answer()


# ── ADMIN: TASDIQLASH / RAD ETISH ────────────────

@router.callback_query(F.data.startswith("confirm_pay:"))
async def confirm_payment(callback: CallbackQuery, bot: Bot):
    purchase_id = int(callback.data.split(":")[1])
    purchase    = await get_purchase_by_id(purchase_id)
    if not purchase:
        await callback.answer("❌ To'lov topilmadi!")
        return

    await confirm_purchase(purchase_id, callback.from_user.id)

    tid = purchase.telegram_id
    pt  = purchase.product_type

    # ── Obuna berish ──────────────────────────
    if pt in ('daily', 'monthly'):
        await grant_subscription(tid, pt, purchase_id)
        LABELS = {'daily': "Kunlik obuna (24 soat)", 'monthly': "Oylik obuna (30 kun)"}
        try:
            await bot.send_message(
                chat_id      = tid,
                text         = (
                    f"✅ <b>To'lovingiz tasdiqlandi!</b>\n\n"
                    f"🎉 {LABELS[pt]} faollashtirildi.\n\n"
                    f"Barcha bo'limlardan testlarni ishlashingiz mumkin!"
                ),
                reply_markup = main_menu_keyboard(),
                parse_mode   = "HTML"
            )
        except Exception:
            pass



    # ── Milliy sertifikat ─────────────────────
    elif pt == 'milliy':
        questions = await get_questions(
            subject='milliy', category='milliy', is_attestation=True, count=44
        )
        meta    = {
            "subject": "milliy", "category": "milliy",
            "is_attestation": True, "solution_url": config.SOLUTION_URL
        }
        q_list  = questions_to_miniapp(questions)
        q_list  = await resolve_image_urls(q_list, bot)
        encoded = encode_questions(q_list, meta)
        url     = f"{config.MINI_APP_URL.rstrip('/')}/?data={encoded}"
        try:
            await bot.send_message(
                chat_id      = tid,
                text         = "✅ <b>To'lovingiz tasdiqlandi!</b>\n\n🏅 Milliy sertifikat testi 👇",
                reply_markup = make_test_keyboard(url),
                parse_mode   = "HTML"
            )
        except Exception:
            pass

    # ── Attestatsiya (har bo'lim alohida) ─────
    elif pt == 'attestation':
        # retry_key = "bolim_1" ... "bolim_10"
        bolim_key = purchase.retry_key or "attestation"
        await grant_attestation(tid, bolim_key, "miniapp")
        # Bo'lim nomini chiroyli ko'rsatish
        if bolim_key.startswith("bolim_"):
            bolim_num  = bolim_key.split("_")[1]
            bolim_text = f"{bolim_num}-bo'lim"
        else:
            bolim_text = "bo'lim"
        try:
            await bot.send_message(
                chat_id    = tid,
                text       = (
                    f"🎓 <b>Atestatsiya — {bolim_text} sotib olindi!</b>\n\n"
                    f"Testni boshlash uchun {bolim_text}ni tanlang:"
                ),
                reply_markup = attestation_bolimlar_keyboard(),
                parse_mode   = "HTML"
            )
        except Exception:
            pass

    # ── Chekni yangilash ──────────────────────
    try:
        await callback.message.edit_caption(
            caption      = (callback.message.caption or "") + "\n\n✅ <b>TASDIQLANDI</b>",
            reply_markup = None,
            parse_mode   = "HTML"
        )
    except Exception:
        pass
    await callback.answer("✅ Tasdiqlandi!")


@router.callback_query(F.data.startswith("reject_pay:"))
async def reject_payment(callback: CallbackQuery, bot: Bot):
    purchase_id = int(callback.data.split(":")[1])
    purchase    = await get_purchase_by_id(purchase_id)
    if not purchase:
        await callback.answer("❌ To'lov topilmadi!")
        return

    await reject_purchase(purchase_id, callback.from_user.id)
    try:
        await bot.send_message(
            chat_id    = purchase.telegram_id,
            text       = "❌ <b>To'lovingiz rad etildi.</b>\n\nBog'lanish uchun adminga murojaat qiling.",
            parse_mode = "HTML"
        )
    except Exception:
        pass

    try:
        await callback.message.edit_caption(
            caption      = (callback.message.caption or "") + "\n\n❌ <b>RAD ETILDI</b>",
            reply_markup = None,
            parse_mode   = "HTML"
        )
    except Exception:
        pass
    await callback.answer("❌ Rad etildi.")


# ── KUTAYOTGAN TO'LOVLAR ──────────────────────────

@router.message(F.text == "💰 Kutayotgan to'lovlar")
async def pending_payments(message: Message):
    if message.from_user.id not in config.ADMIN_IDS:
        return

    purchases = await get_pending_purchases()
    if not purchases:
        await message.answer("✅ Kutayotgan to'lovlar yo'q.")
        return

    LABELS = {
        'daily': 'Kunlik',
        'monthly': 'Oylik', 'attestation': 'Atestatsiya',
    }
    for p, user in purchases:
        uname = f"@{user.username}" if user and user.username else str(p.telegram_id)
        label = LABELS.get(p.product_type, p.product_type)
        await message.bot.send_photo(
            chat_id      = message.from_user.id,
            photo        = p.check_photo,
            caption      = (
                f"💰 <b>To'lov #{p.id}</b>\n"
                f"👤 {user.full_name if user else '?'} | {uname}\n"
                f"📦 {label} — {p.amount:,} so'm\n"
                f"🕐 {str(p.submitted_at)[:16]}"
            ),
            reply_markup = payment_confirm_keyboard(p.id),
            parse_mode   = "HTML"
        )