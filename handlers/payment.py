"""
To'lov tizimi — yangi:
  once    — 3,500 so'm (bir martalik, bitta test)
  daily   — 35,000 so'm (24 soat barcha testlar)
  monthly — 100,000 so'm (30 kun barcha testlar)
  attestation — bir martalik atestatsiya
"""
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from database.db import (
    create_purchase, confirm_purchase, reject_purchase,
    get_purchase_by_id, get_pending_purchases,
    grant_attestation, get_user
)
from database.db import grant_subscription  # yangi funksiya
from keyboards.keyboards import (
    cancel_keyboard, payment_confirm_keyboard,
    main_menu_keyboard, attestation_format_keyboard
)
from states import PaymentStates
from config import config

router = Router()

PRODUCT_LABELS = {
    'once':    "Bir martalik — 3,500 so'm",
    'daily':   "Kunlik — 35,000 so'm",
    'monthly': "Oylik — 100,000 so'm",
}
PRODUCT_PRICES = {
    'once':    3_500,
    'daily':   35_000,
    'monthly': 100_000,
}

# ── TO'LOV BOSHLASH ────────────────────────────────

@router.callback_query(F.data.startswith("pay:"))
async def pay_start(callback: CallbackQuery, state: FSMContext):
    # pay:once:onatili:mavzu:fonetika
    # pay:daily:onatili:mavzu:fonetika
    # pay:monthly:onatili:mavzu:fonetika
    parts    = callback.data.split(":", 2)
    pay_type = parts[1]           # once | daily | monthly
    key      = parts[2]           # access_key (once uchun) yoki ixtiyoriy (daily/monthly)

    amount = PRODUCT_PRICES.get(pay_type, 0)
    label  = PRODUCT_LABELS.get(pay_type, '')

    await state.update_data(
        product_type=pay_type,
        retry_key=key,
        amount=amount
    )

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

# Attestation to'lov
@router.callback_query(F.data.startswith("buy:attestation:"))
async def attestation_pay_start(callback: CallbackQuery, state: FSMContext):
    subject = callback.data.split(":")[2]
    SUBJ = {'onatili': 'Ona tili', 'adabiyot': 'Adabiyot'}
    amount = config.PRICE_ATTESTATION

    await state.update_data(
        product_type=f'attestation_{subject}',
        retry_key=None,
        amount=amount
    )
    await callback.message.edit_text(
        f"🎓 <b>{SUBJ.get(subject)} Atestatsiya</b>\n\n"
        f"To'lov miqdori: <b>{amount:,} so'm</b>\n\n"
        f"Kartaga o'tkazing:\n"
        f"<code>{config.PAYMENT_CARD}</code>\n"
        f"<b>{config.PAYMENT_OWNER}</b>\n\n"
        f"Chek rasmini yuboring 👇",
        reply_markup=cancel_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(PaymentStates.waiting_for_check)
    await callback.answer()

# Attestation standalone to'lov (fan ajratilmagan)
@router.callback_query(F.data == "buy:attestation")
async def attestation_pay_standalone(callback: CallbackQuery, state: FSMContext):
    amount = config.PRICE_ATTESTATION
    await state.update_data(
        product_type='attestation',
        retry_key=None,
        amount=amount
    )
    await callback.message.edit_text(
        f"🎓 <b>Atestatsiya</b>\n\n"
        f"To'lov miqdori: <b>{amount:,} so'm</b>\n\n"
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

    file_id = message.photo[-1].file_id

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

    # Adminlarga xabar
    LABELS = {
        'once':    "Bir martalik (3,500)",
        'daily':   "Kunlik (35,000)",
        'monthly': "Oylik (100,000)",
    }
    user = await get_user(message.from_user.id)
    uname = f"@{user.username}" if user and user.username else str(message.from_user.id)

    label = LABELS.get(product_type, product_type)
    key_info = f"\n🔑 Key: <code>{retry_key}</code>" if retry_key and product_type == 'once' else ""

    for admin_id in config.ADMIN_IDS:
        try:
            await bot.send_photo(
                chat_id  = admin_id,
                photo    = file_id,
                caption  = (
                    f"💰 <b>Yangi to'lov #{purchase_id}</b>\n\n"
                    f"👤 {user.full_name if user else '?'} | {uname}\n"
                    f"📦 Turi: <b>{label}</b>{key_info}\n"
                    f"💵 Summa: <b>{amount:,} so'm</b>"
                ),
                reply_markup=payment_confirm_keyboard(purchase_id),
                parse_mode="HTML"
            )
        except Exception:
            pass

@router.message(PaymentStates.waiting_for_check)
async def check_not_photo(message: Message):
    if message.text == "❌ Bekor qilish":
        return
    await message.answer("📸 Iltimos, <b>rasm</b> (chek screenshot) yuboring.",
                         parse_mode="HTML")

# ── BEKOR QILISH ──────────────────────────────────

@router.callback_query(F.data == "payment:cancel")
async def payment_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Bekor qilindi.", reply_markup=main_menu_keyboard())
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

    # Obuna yoki kirish berish
    tid = purchase.telegram_id
    pt  = purchase.product_type

    if pt in ('daily', 'monthly'):
        await grant_subscription(tid, pt, purchase_id)
        LABELS = {'daily': "Kunlik obuna (24 soat)", 'monthly': "Oylik obuna (30 kun)"}
        try:
            await bot.send_message(
                chat_id    = tid,
                text       = f"✅ <b>To'lovingiz tasdiqlandi!</b>\n\n🎉 {LABELS.get(pt)} faollashtirildi.\n\nEndi barcha bo'limlardan testlarni ishlashingiz mumkin!",
                reply_markup=main_menu_keyboard(),
                parse_mode = "HTML"
            )
        except Exception:
            pass

    elif pt == 'once':
        # access_key orqali test linkini yaratib yuborish
        access_key = purchase.retry_key or ''
        try:
            if access_key and ':' in access_key:
                parts = access_key.split(':')
                subject    = parts[0] if len(parts) > 0 else 'onatili'
                category   = parts[1] if len(parts) > 1 else 'aralash'
                subcategory = parts[2] if len(parts) > 2 and parts[2] != 'None' else None

                from database.db import get_questions, count_questions
                from handlers.test_handler import (
                    questions_to_miniapp, encode_questions,
                    resolve_image_urls
                )
                from keyboards.keyboards import miniapp_keyboard
                from config import config

                cnt = await count_questions(subject=subject, category=category, subcategory=subcategory)
                questions = await get_questions(
                    subject=subject, category=category,
                    subcategory=subcategory, difficulty=None,
                    count=min(cnt, config.MAX_QUESTIONS)
                )
                meta = {'subject': subject, 'category': category,
                        'subcategory': subcategory, 'is_attestation': False,
                        'solution_url': config.SOLUTION_URL}
                q_list  = questions_to_miniapp(questions)
                q_list  = await resolve_image_urls(q_list, bot)
                encoded = encode_questions(q_list, meta)
                url     = f"{config.MINI_APP_URL.rstrip('/')}/?data={encoded}"

                await bot.send_message(
                    chat_id    = tid,
                    text       = f"✅ <b>To'lovingiz tasdiqlandi!</b>\n\n🎉 Testni boshlashingiz mumkin 👇",
                    reply_markup=miniapp_keyboard(url),
                    parse_mode = "HTML"
                )
            else:
                await bot.send_message(
                    chat_id    = tid,
                    text       = "✅ <b>To'lovingiz tasdiqlandi!</b>\n\n🎉 Bir martalik kirish faollashtirildi.",
                    reply_markup=main_menu_keyboard(),
                    parse_mode = "HTML"
                )
        except Exception as e:
            await bot.send_message(
                chat_id    = tid,
                text       = "✅ <b>To'lovingiz tasdiqlandi!</b>\n\nTestni boshlash uchun bo'limni tanlang.",
                reply_markup=main_menu_keyboard(),
                parse_mode = "HTML"
            )

    elif pt == 'milliy':
        from database.db import get_questions
        from handlers.test_handler import (
            questions_to_miniapp, encode_questions, resolve_image_urls
        )
        from keyboards.keyboards import miniapp_keyboard
        from config import config
        questions = await get_questions(subject="milliy", category="milliy", is_attestation=True, count=44)
        meta = {"subject": "milliy", "category": "milliy", "is_attestation": True, "solution_url": config.SOLUTION_URL}
        q_list  = questions_to_miniapp(questions)
        q_list  = await resolve_image_urls(q_list, bot)
        encoded = encode_questions(q_list, meta)
        url     = f"{config.MINI_APP_URL.rstrip('/')}/?data={encoded}"
        try:
            await bot.send_message(
                chat_id    = tid,
                text       = "✅ <b>To'lovingiz tasdiqlandi!</b>\n\n🏅 Milliy sertifikat testi 👇",
                reply_markup=miniapp_keyboard(url),
                parse_mode = "HTML"
            )
        except Exception:
            pass

    elif pt == 'attestation':
        await grant_attestation(tid, "attestation", "miniapp")
        from database.db import get_questions
        from handlers.test_handler import (
            questions_to_miniapp, encode_questions, resolve_image_urls
        )
        from keyboards.keyboards import miniapp_keyboard
        from config import config
        questions = await get_questions(subject="attestation", category="attestation", is_attestation=True, count=config.ATTESTATION_COUNT)
        meta = {"subject": "attestation", "category": "attestation", "is_attestation": True, "solution_url": config.SOLUTION_URL}
        q_list  = questions_to_miniapp(questions)
        q_list  = await resolve_image_urls(q_list, bot)
        encoded = encode_questions(q_list, meta)
        url     = f"{config.MINI_APP_URL.rstrip('/')}/?data={encoded}"
        try:
            await bot.send_message(
                chat_id    = tid,
                text       = "🎓 <b>Atestatsiya sotib olindi!</b>\n\nTestni boshlang 👇",
                reply_markup=miniapp_keyboard(url),
                parse_mode = "HTML"
            )
        except Exception:
            pass

    await callback.message.edit_caption(
        caption      = callback.message.caption + "\n\n✅ <b>TASDIQLANDI</b>",
        reply_markup = None,
        parse_mode   = "HTML"
    )
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

    await callback.message.edit_caption(
        caption      = callback.message.caption + "\n\n❌ <b>RAD ETILDI</b>",
        reply_markup = None,
        parse_mode   = "HTML"
    )
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

    for p, user in purchases:
        uname = f"@{user.username}" if user and user.username else str(p.telegram_id)
        LABELS = {'once': 'Bir martalik', 'daily': 'Kunlik', 'monthly': 'Oylik',
               'attestation': 'Atestatsiya'}
        label  = LABELS.get(p.product_type, p.product_type)

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