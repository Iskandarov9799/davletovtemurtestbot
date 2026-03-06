import io
import openpyxl
from aiogram import Router, F, Bot
from aiogram.types import Message, BufferedInputFile
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command

from database.db import (
    get_all_users, get_pending_payments, get_full_stats,
    get_daily_stats, add_question
)
from keyboards.keyboards import admin_keyboard, main_menu_keyboard, cancel_keyboard, skip_keyboard
from states import AdminStates
from config import config

router = Router()

def is_admin(user_id):
    return user_id in config.ADMIN_IDS

# ============ ADMIN PANEL ============

@router.message(Command("admin"))
async def admin_panel(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Siz admin emassiz!")
        return
    await message.answer("🔐 <b>Admin panel</b>", reply_markup=admin_keyboard(), parse_mode="HTML")

@router.message(F.text == "🔙 Orqaga")
async def back_handler(message: Message, state: FSMContext):
    await state.clear()
    from database.db import is_user_paid
    paid = is_user_paid(message.from_user.id)
    await message.answer("🔙 Asosiy menyu", reply_markup=main_menu_keyboard(is_paid=paid))

# ============ STATISTIKA ============

@router.message(F.text == "📊 Statistika")
async def statistics(message: Message):
    if not is_admin(message.from_user.id):
        return
    s = get_full_stats()
    daily = get_daily_stats()

    daily_text = ""
    for row in daily:
        daily_text += f"  📅 {row['date']}: +{row['new_users']} foydalanuvchi\n"

    income = s['paid'] * config.PAYMENT_AMOUNT
    await message.answer(
        f"📊 <b>Bot Statistikasi</b>\n\n"
        f"👥 Jami: <b>{s['total_users']}</b>\n"
        f"✅ Ro'yxatdan o'tgan: <b>{s['registered']}</b>\n"
        f"💰 To'lov tasdiqlangan: <b>{s['paid']}</b>\n"
        f"⏳ Kutayotgan to'lov: <b>{s['pending_payments']}</b>\n"
        f"📝 Jami testlar: <b>{s['total_tests']}</b>\n"
        f"📈 O'rtacha ball: <b>{s['avg_score']}%</b>\n"
        f"❓ Savollar soni: <b>{s['total_questions']}</b>\n"
        f"💵 Jami daromad: <b>{income:,} so'm</b>\n\n"
        f"<b>So'nggi 7 kun:</b>\n{daily_text if daily_text else '  Ma\'lumot yo\'q'}",
        parse_mode="HTML"
    )

# ============ FOYDALANUVCHILAR ============

@router.message(F.text == "👥 Foydalanuvchilar")
async def all_users_handler(message: Message):
    if not is_admin(message.from_user.id):
        return
    users = get_all_users()
    total = len(users)
    paid = sum(1 for u in users if u['payment_confirmed'])
    registered = sum(1 for u in users if u['is_registered'])

    text = (
        f"👥 <b>Foydalanuvchilar: {total}</b>\n"
        f"✅ Ro'yxat: {registered}  |  💰 To'lov: {paid}\n\n"
        f"<b>So'nggi 15 ta:</b>\n"
    )
    for u in users[:15]:
        icon = "💰" if u['payment_confirmed'] else ("⏳" if u['is_paid'] else "👤")
        name = u['full_name'] or "Noma'lum"
        phone = u['phone_number'] or "—"
        text += f"{icon} {name} | {phone}\n"

    await message.answer(text, parse_mode="HTML")

# ============ EXCEL EKSPORT ============

@router.message(F.text == "📥 Excel eksport")
async def excel_export(message: Message):
    if not is_admin(message.from_user.id):
        return

    users = get_all_users()
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Foydalanuvchilar"

    headers = ["ID", "Telegram ID", "Ism", "Username", "Telefon",
               "Ro'yxat", "To'lov", "Tasdiqlangan", "Ro'yxat sanasi", "To'lov sanasi"]
    ws.append(headers)

    for u in users:
        ws.append([
            u['id'],
            u['telegram_id'],
            u['full_name'] or "",
            u['username'] or "",
            u['phone_number'] or "",
            "Ha" if u['is_registered'] else "Yo'q",
            "Ha" if u['is_paid'] else "Yo'q",
            "Ha" if u['payment_confirmed'] else "Yo'q",
            (u['registered_at'] or "")[:16],
            (u['paid_at'] or "")[:16],
        ])

    # Ustun kengligini avtomatik sozlash
    for col in ws.columns:
        max_len = max(len(str(cell.value or "")) for cell in col)
        ws.column_dimensions[col[0].column_letter].width = min(max_len + 2, 30)

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)

    filename = f"users_{message.date.strftime('%Y%m%d')}.xlsx"
    await message.answer_document(
        document=BufferedInputFile(buf.read(), filename=filename),
        caption=f"📥 Foydalanuvchilar ro'yxati\n👥 Jami: {len(users)} ta"
    )

# ============ BROADCAST ============

@router.message(F.text == "📢 Broadcast")
async def broadcast_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await message.answer(
        "📢 <b>Broadcast</b>\n\nBarcha foydalanuvchilarga yuboriladigan xabarni yozing:\n\n"
        "(Matn, rasm yoki video yuborishingiz mumkin)",
        reply_markup=cancel_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(AdminStates.broadcast_text)

@router.message(AdminStates.broadcast_text, F.text == "❌ Bekor qilish")
async def broadcast_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Bekor qilindi.", reply_markup=admin_keyboard())

@router.message(AdminStates.broadcast_text)
async def broadcast_send(message: Message, state: FSMContext, bot: Bot):
    if not is_admin(message.from_user.id):
        return

    await state.clear()
    users = get_all_users()
    registered_users = [u for u in users if u['is_registered']]

    sent = 0
    failed = 0
    status_msg = await message.answer(f"📤 Yuborilmoqda... (0/{len(registered_users)})")

    for i, user in enumerate(registered_users):
        try:
            if message.photo:
                await bot.send_photo(
                    chat_id=user['telegram_id'],
                    photo=message.photo[-1].file_id,
                    caption=message.caption or ""
                )
            elif message.video:
                await bot.send_video(
                    chat_id=user['telegram_id'],
                    video=message.video.file_id,
                    caption=message.caption or ""
                )
            else:
                await bot.send_message(chat_id=user['telegram_id'], text=message.text)
            sent += 1
        except Exception:
            failed += 1

        if (i + 1) % 10 == 0:
            try:
                await status_msg.edit_text(f"📤 Yuborilmoqda... ({i+1}/{len(registered_users)})")
            except Exception:
                pass

    await status_msg.edit_text(
        f"✅ <b>Broadcast yakunlandi!</b>\n\n"
        f"📤 Yuborildi: <b>{sent}</b>\n"
        f"❌ Xato: <b>{failed}</b>",
        parse_mode="HTML"
    )
    await message.answer("Admin panel:", reply_markup=admin_keyboard())

# ============ SAVOL QO'SHISH ============

@router.message(F.text == "➕ Savol qo'shish")
async def add_question_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await message.answer(
        "➕ <b>Yangi savol qo'shish</b>\n\nQiyinlik darajasini yozing:\n"
        "<code>easy</code> — oson\n<code>medium</code> — o'rta\n<code>hard</code> — qiyin",
        reply_markup=cancel_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(AdminStates.add_q_difficulty)

@router.message(AdminStates.add_q_difficulty, F.text == "❌ Bekor qilish")
async def add_q_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Bekor qilindi.", reply_markup=admin_keyboard())

@router.message(AdminStates.add_q_difficulty)
async def add_q_get_difficulty(message: Message, state: FSMContext):
    diff = message.text.strip().lower()
    if diff not in ['easy', 'medium', 'hard']:
        await message.answer("❌ Faqat: easy, medium yoki hard yozing!")
        return
    await state.update_data(difficulty=diff)
    await message.answer("📸 Savol rasmi bormi? Rasmni yuboring yoki o'tkazib yuboring:", reply_markup=skip_keyboard())
    await state.set_state(AdminStates.add_q_image)

@router.message(AdminStates.add_q_image, F.photo)
async def add_q_get_image(message: Message, state: FSMContext):
    await state.update_data(image_file_id=message.photo[-1].file_id)
    await message.answer("❓ Savol matnini yozing:", reply_markup=cancel_keyboard())
    await state.set_state(AdminStates.add_q_text)

@router.message(AdminStates.add_q_image, F.text == "⏭ Rasmisiz davom etish")
async def add_q_skip_image(message: Message, state: FSMContext):
    await state.update_data(image_file_id=None)
    await message.answer("❓ Savol matnini yozing:", reply_markup=cancel_keyboard())
    await state.set_state(AdminStates.add_q_text)

@router.message(AdminStates.add_q_text)
async def add_q_get_text(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("❌ Bekor qilindi.", reply_markup=admin_keyboard())
        return
    await state.update_data(question_text=message.text)
    await message.answer("🅰 A variantini yozing:")
    await state.set_state(AdminStates.add_q_a)

@router.message(AdminStates.add_q_a)
async def add_q_get_a(message: Message, state: FSMContext):
    await state.update_data(option_a=message.text)
    await message.answer("🅱 B variantini yozing:")
    await state.set_state(AdminStates.add_q_b)

@router.message(AdminStates.add_q_b)
async def add_q_get_b(message: Message, state: FSMContext):
    await state.update_data(option_b=message.text)
    await message.answer("🅲 C variantini yozing:")
    await state.set_state(AdminStates.add_q_c)

@router.message(AdminStates.add_q_c)
async def add_q_get_c(message: Message, state: FSMContext):
    await state.update_data(option_c=message.text)
    await message.answer("🅳 D variantini yozing:")
    await state.set_state(AdminStates.add_q_d)

@router.message(AdminStates.add_q_d)
async def add_q_get_d(message: Message, state: FSMContext):
    await state.update_data(option_d=message.text)
    data = await state.get_data()
    await message.answer(
        f"✅ <b>Savol sharhi:</b>\n\n"
        f"❓ {data['question_text']}\n\n"
        f"A: {data['option_a']}\n"
        f"B: {data['option_b']}\n"
        f"C: {data['option_c']}\n"
        f"D: {data['option_d']}\n\n"
        f"To'g'ri javobni yozing (A, B, C yoki D):",
        parse_mode="HTML"
    )
    await state.set_state(AdminStates.add_q_correct)

@router.message(AdminStates.add_q_correct)
async def add_q_get_correct(message: Message, state: FSMContext):
    correct = message.text.strip().upper()
    if correct not in ['A', 'B', 'C', 'D']:
        await message.answer("❌ Faqat A, B, C yoki D yozing!")
        return

    data = await state.get_data()
    add_question(
        subject="ona_tili",
        question_text=data['question_text'],
        option_a=data['option_a'],
        option_b=data['option_b'],
        option_c=data['option_c'],
        option_d=data['option_d'],
        correct_answer=correct,
        difficulty=data['difficulty'],
        image_file_id=data.get('image_file_id')
    )
    await state.clear()
    await message.answer(
        "✅ <b>Savol muvaffaqiyatli qo'shildi!</b>",
        reply_markup=admin_keyboard(),
        parse_mode="HTML"
    )