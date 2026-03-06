from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.filters import CommandStart, Command

from database.db import get_user, create_user, update_user_phone, is_user_paid
from keyboards.keyboards import phone_keyboard, main_menu_keyboard
from states import RegistrationStates
from config import config

router = Router()

# ============ /start ============

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
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
        payment_status = "✅ To'lovingiz tasdiqlangan!" if paid else "⏳ To'lovingizni amalga oshiring."
        await message.answer(
            f"👋 Xush kelibsiz, <b>{message.from_user.full_name}</b>!\n\n"
            f"{payment_status}",
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

# ============ /test ============

@router.message(Command("test"))
async def cmd_test(message: Message, state: FSMContext):
    from database.db import is_user_registered
    if not is_user_registered(message.from_user.id):
        await message.answer("❌ Avval ro'yxatdan o'ting! /start")
        return
    if not is_user_paid(message.from_user.id):
        await message.answer(
            "❌ Test uchun to'lov qilishingiz kerak!\n💳 /pay buyrug'ini yuboring."
        )
        return
    from keyboards.keyboards import difficulty_keyboard
    from states import TestStates
    await message.answer("🎯 <b>Qiyinlik darajasini tanlang:</b>", reply_markup=difficulty_keyboard(), parse_mode="HTML")
    await state.set_state(TestStates.choosing_difficulty)

# ============ /pay ============

@router.message(Command("pay"))
async def cmd_pay(message: Message, state: FSMContext):
    from database.db import is_user_registered
    if not is_user_registered(message.from_user.id):
        await message.answer("❌ Avval ro'yxatdan o'ting! /start")
        return
    if is_user_paid(message.from_user.id):
        await message.answer("✅ Siz allaqachon to'lov qilgansiz!\n📝 /test buyrug'i bilan testni boshlang.")
        return
    from keyboards.keyboards import cancel_keyboard
    from states import PaymentStates
    await message.answer(
        f"💳 <b>To'lov ma'lumotlari</b>\n\n"
        f"💰 Summa: <b>{config.PAYMENT_AMOUNT:,} so'm</b>\n\n"
        f"🏦 Karta raqami:\n<code>{config.PAYMENT_CARD_NUMBER}</code>\n\n"
        f"👤 Karta egasi: <b>{config.PAYMENT_CARD_OWNER}</b>\n\n"
        f"📸 To'lovni amalga oshirgach, <b>to'lov chekining rasmini</b> yuboring.",
        parse_mode="HTML",
        reply_markup=cancel_keyboard()
    )
    await state.set_state(PaymentStates.waiting_for_check)

# ============ /results ============

@router.message(Command("results"))
async def cmd_results(message: Message):
    from database.db import get_user_results
    results = get_user_results(message.from_user.id)
    if not results:
        await message.answer("📊 Hali test ishlamagansiz.\n📝 /test buyrug'i bilan boshlang!")
        return
    DIFFICULTY_NAMES = {'easy': '🟢 Oson', 'medium': "🟡 O'rta", 'hard': '🔴 Qiyin', 'mixed': '🎲 Aralash'}
    text = "📊 <b>Sizning natijalaringiz:</b>\n\n"
    for i, r in enumerate(results, 1):
        date = r['finished_at'][:10] if r['finished_at'] else "—"
        diff = DIFFICULTY_NAMES.get(r['difficulty'], r['difficulty'])
        text += f"{i}. 📅 {date}  {diff}\n   ✅ {r['correct_answers']}/30  📈 {r['score']}%\n\n"
    await message.answer(text, parse_mode="HTML")

# ============ /top ============

@router.message(Command("top"))
async def cmd_top(message: Message):
    from database.db import get_leaderboard
    leaders = get_leaderboard(10)
    if not leaders:
        await message.answer("🏆 Hali reyting mavjud emas!")
        return
    medals = ["🥇", "🥈", "🥉"] + ["4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
    text = "🏆 <b>Eng yaxshi natijalar:</b>\n\n"
    for i, row in enumerate(leaders):
        name = row['full_name'] or "Noma'lum"
        medal = medals[i] if i < len(medals) else f"{i+1}."
        text += f"{medal} <b>{name}</b> — {row['best_score']}%  ({row['attempts']} marta)\n"
    await message.answer(text, parse_mode="HTML")

# ============ /info ============

@router.message(Command("info"))
@router.message(F.text == "ℹ️ Ma'lumot")
async def info_handler(message: Message):
    await message.answer(
        "📚 <b>Ona tili va Adabiyot Test Boti</b>\n\n"
        "🎯 <b>Qanday ishlaydi?</b>\n"
        "1️⃣ Telefon raqamingizni ulashing\n"
        "2️⃣ To'lov qiling va chekni yuboring\n"
        "3️⃣ Admin tasdiqlaydi\n"
        "4️⃣ 30 ta random savol ishlang\n"
        "5️⃣ Natijangizni ko'ring!\n\n"
        f"💰 <b>Narxi:</b> {config.PAYMENT_AMOUNT:,} so'm\n\n"
        "📞 <b>Muammo bo'lsa:</b> @admin_username\n\n"
        "<b>Buyruqlar:</b>\n"
        "/start — Boshlanish\n"
        "/test — Testni boshlash\n"
        "/pay — To'lov qilish\n"
        "/results — Natijalarim\n"
        "/top — Reyting\n"
        "/info — Ma'lumot",
        parse_mode="HTML"
    )

# ============ /admin ============

@router.message(Command("admin"))
async def cmd_admin(message: Message):
    if message.from_user.id not in config.ADMIN_IDS:
        await message.answer("⛔ Siz admin emassiz!")
        return
    from keyboards.keyboards import admin_keyboard
    await message.answer(
        "🔐 <b>Admin panel</b>\n\nQuyidagi amallardan birini tanlang:",
        reply_markup=admin_keyboard(),
        parse_mode="HTML"
    )

# ============ Admin buyruqlari ============

@router.message(Command("stats"))
async def cmd_stats(message: Message):
    if message.from_user.id not in config.ADMIN_IDS:
        await message.answer("⛔ Ruxsat yo'q!")
        return
    from database.db import get_full_stats, get_daily_stats
    s = get_full_stats()
    daily = get_daily_stats()
    daily_text = "".join(f"  📅 {r['date']}: +{r['new_users']}\n" for r in daily)
    income = s['paid'] * config.PAYMENT_AMOUNT
    await message.answer(
        f"📊 <b>Statistika</b>\n\n"
        f"👥 Jami: <b>{s['total_users']}</b>\n"
        f"✅ Ro'yxat: <b>{s['registered']}</b>\n"
        f"💰 To'lov: <b>{s['paid']}</b>\n"
        f"⏳ Kutayotgan: <b>{s['pending_payments']}</b>\n"
        f"📝 Testlar: <b>{s['total_tests']}</b>\n"
        f"📈 O'rtacha: <b>{s['avg_score']}%</b>\n"
        f"❓ Savollar: <b>{s['total_questions']}</b>\n"
        f"💵 Daromad: <b>{income:,} so'm</b>\n\n"
        f"<b>So'nggi 7 kun:</b>\n{daily_text or 'Malumot yoq'}",
        parse_mode="HTML"
    )

@router.message(Command("users"))
async def cmd_users(message: Message):
    if message.from_user.id not in config.ADMIN_IDS:
        await message.answer("⛔ Ruxsat yo'q!")
        return
    from database.db import get_all_users
    users = get_all_users()
    total = len(users)
    paid = sum(1 for u in users if u['payment_confirmed'])
    text = f"👥 <b>Foydalanuvchilar: {total}</b>  |  💰 To'lov: {paid}\n\n"
    for u in users[:15]:
        icon = "💰" if u['payment_confirmed'] else ("⏳" if u['is_paid'] else "👤")
        text += f"{icon} {u['full_name'] or 'Nomalum'} | {u['phone_number'] or '—'}\n"
    await message.answer(text, parse_mode="HTML")

@router.message(Command("export"))
async def cmd_export(message: Message):
    if message.from_user.id not in config.ADMIN_IDS:
        await message.answer("⛔ Ruxsat yo'q!")
        return
    import io
    import openpyxl
    from aiogram.types import BufferedInputFile
    from database.db import get_all_users
    users = get_all_users()
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Foydalanuvchilar"
    ws.append(["ID", "Telegram ID", "Ism", "Username", "Telefon", "Royxat", "Tolov", "Tasdiqlangan", "Sana"])
    for u in users:
        ws.append([
            u['id'], u['telegram_id'], u['full_name'] or "",
            u['username'] or "", u['phone_number'] or "",
            "Ha" if u['is_registered'] else "Yoq",
            "Ha" if u['is_paid'] else "Yoq",
            "Ha" if u['payment_confirmed'] else "Yoq",
            (u['registered_at'] or "")[:16]
        ])
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    await message.answer_document(
        document=BufferedInputFile(buf.read(), filename="users.xlsx"),
        caption=f"📥 Jami: {len(users)} ta foydalanuvchi"
    )

@router.message(Command("broadcast"))
async def cmd_broadcast(message: Message, state: FSMContext):
    if message.from_user.id not in config.ADMIN_IDS:
        await message.answer("⛔ Ruxsat yo'q!")
        return
    from keyboards.keyboards import cancel_keyboard
    from states import AdminStates
    await message.answer(
        "📢 Barcha foydalanuvchilarga yuboriladigan xabarni yozing:",
        reply_markup=cancel_keyboard()
    )
    await state.set_state(AdminStates.broadcast_text)

@router.message(Command("addquestion"))
async def cmd_addquestion(message: Message, state: FSMContext):
    if message.from_user.id not in config.ADMIN_IDS:
        await message.answer("⛔ Ruxsat yo'q!")
        return
    from keyboards.keyboards import cancel_keyboard
    from states import AdminStates
    await message.answer(
        "➕ <b>Yangi savol qo'shish</b>\n\nQiyinlik darajasini yozing:\n"
        "<code>easy</code> — oson\n<code>medium</code> — o'rta\n<code>hard</code> — qiyin",
        reply_markup=cancel_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(AdminStates.add_q_difficulty)

# ============ Telefon qabul qilish ============

@router.message(RegistrationStates.waiting_for_phone, F.contact)
async def process_phone(message: Message, state: FSMContext):
    contact = message.contact
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
        f"💳 Test uchun to'lov qilishingiz kerak.\n"
        f"Narxi: <b>{config.PAYMENT_AMOUNT:,} so'm</b>\n\n"
        f"/pay buyrug'i orqali to'lov qiling.",
        reply_markup=main_menu_keyboard(is_paid=False),
        parse_mode="HTML"
    )

@router.message(RegistrationStates.waiting_for_phone)
async def wrong_contact(message: Message):
    await message.answer(
        "📱 Iltimos, quyidagi tugmani bosib telefon raqamingizni ulashing:",
        reply_markup=phone_keyboard()
    )