import io
import openpyxl
from aiogram import Router, F, Bot
from aiogram.types import Message, BufferedInputFile
from aiogram.fsm.context import FSMContext

from database.db import (
    get_all_users, get_full_stats, add_question,
    count_questions
)
from keyboards.keyboards import (
    admin_keyboard, cancel_keyboard, main_menu_keyboard,
    subject_keyboard, addq_category_keyboard, addq_topic_keyboard,
    addq_grade_keyboard, addq_difficulty_keyboard, correct_answer_keyboard,
    skip_image_keyboard
)
from states import AdminStates
from config import config

router = Router()

# ══════════════════════════════════════════════
# ADMIN PANEL
# ══════════════════════════════════════════════

def is_admin(message: Message) -> bool:
    return message.from_user.id in config.ADMIN_IDS

# ══════════════════════════════════════════════
# FOYDALANUVCHILAR RO'YXATI
# ══════════════════════════════════════════════

@router.message(F.text == "👥 Foydalanuvchilar")
async def admin_users(message: Message):
    if not is_admin(message): return

    users = await get_all_users()
    total = len(users)
    text  = f"👥 <b>Foydalanuvchilar: {total} ta</b>\n\n"

    for u in users[:20]:
        icon  = "✅" if u.is_registered else "👤"
        uname = f"@{u.username}" if u.username else "—"
        text += f"{icon} {u.full_name or 'Noma\'lum'} | {u.phone_number or '—'} | {uname}\n"

    if total > 20:
        text += f"\n... va yana {total - 20} ta"

    await message.answer(text, parse_mode="HTML")

# ══════════════════════════════════════════════
# EXCEL EKSPORT
# ══════════════════════════════════════════════

@router.message(F.text == "📥 Excel eksport")
async def admin_export(message: Message):
    if not is_admin(message): return

    users = await get_all_users()
    wb    = openpyxl.Workbook()
    ws    = wb.active
    ws.title = "Foydalanuvchilar"

    # Sarlavha
    ws.append(["#", "Telegram ID", "Ism", "Username", "Telefon", "Ro'yxat", "Sana"])
    for i, u in enumerate(users, 1):
        ws.append([
            i,
            u.telegram_id,
            u.full_name or "",
            u.username or "",
            u.phone_number or "",
            "Ha" if u.is_registered else "Yo'q",
            str(u.registered_at)[:16] if u.registered_at else "",
        ])

    # Ustun kengligini moslashtirish
    for col in ws.columns:
        max_len = max(len(str(cell.value or "")) for cell in col)
        ws.column_dimensions[col[0].column_letter].width = min(max_len + 2, 40)

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)

    await message.answer_document(
        document=BufferedInputFile(buf.read(), filename="users.xlsx"),
        caption=f"📥 Jami: <b>{len(users)}</b> ta foydalanuvchi",
        parse_mode="HTML"
    )

# ══════════════════════════════════════════════
# BROADCAST
# ══════════════════════════════════════════════

@router.message(F.text == "📢 Broadcast")
async def admin_broadcast_start(message: Message, state: FSMContext):
    if not is_admin(message): return
    await message.answer(
        "📢 <b>Broadcast</b>\n\n"
        "Barcha foydalanuvchilarga yuboriladigan xabarni yozing\n"
        "(matn, rasm yoki video yuborishingiz mumkin):",
        reply_markup=cancel_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(AdminStates.broadcast_message)

@router.message(AdminStates.broadcast_message, F.text == "❌ Bekor qilish")
async def broadcast_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Bekor qilindi.", reply_markup=admin_keyboard())

@router.message(AdminStates.broadcast_message)
async def admin_broadcast_send(message: Message, state: FSMContext, bot: Bot):
    await state.clear()
    users   = await get_all_users()
    success = 0
    failed  = 0

    await message.answer(f"⏳ {len(users)} ta foydalanuvchiga yuborilmoqda...")

    for user in users:
        try:
            if message.photo:
                await bot.send_photo(
                    chat_id=user.telegram_id,
                    photo=message.photo[-1].file_id,
                    caption=message.caption or ""
                )
            elif message.video:
                await bot.send_video(
                    chat_id=user.telegram_id,
                    video=message.video.file_id,
                    caption=message.caption or ""
                )
            else:
                await bot.send_message(
                    chat_id=user.telegram_id,
                    text=message.text or ""
                )
            success += 1
        except Exception:
            failed += 1

    await message.answer(
        f"📢 <b>Broadcast tugadi!</b>\n\n"
        f"✅ Yuborildi: <b>{success}</b>\n"
        f"❌ Xato:     <b>{failed}</b>",
        reply_markup=admin_keyboard(),
        parse_mode="HTML"
    )

# ══════════════════════════════════════════════
# SAVOL QO'SHISH
# ══════════════════════════════════════════════

@router.message(F.text == "➕ Savol qo'shish")
async def add_question_start(message: Message, state: FSMContext):
    if not is_admin(message): return
    await message.answer(
        "➕ <b>Yangi savol qo'shish</b>\n\nFanni tanlang:",
        reply_markup=subject_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(AdminStates.add_subject)

# Fan tanlash
from aiogram.types import CallbackQuery

@router.callback_query(F.data.startswith("addq:subject:"))
async def addq_subject(callback: CallbackQuery, state: FSMContext):
    subject = callback.data.split(":")[2]
    await state.update_data(subject=subject)
    SUBJ = {'onatili': '📚 Ona tili', 'adabiyot': '📖 Adabiyot'}
    await callback.message.edit_text(
        f"📁 <b>{SUBJ.get(subject)} — Kategoriya tanlang:</b>",
        reply_markup=addq_category_keyboard(subject),
        parse_mode="HTML"
    )
    await state.set_state(AdminStates.add_category)
    await callback.answer()

# Kategoriya tanlash
@router.callback_query(F.data.startswith("addq:cat:"))
async def addq_category(callback: CallbackQuery, state: FSMContext):
    category = callback.data.split(":")[2]
    await state.update_data(category=category)
    data = await state.get_data()
    subject = data.get('subject')

    if category == 'mavzu':
        await callback.message.edit_text(
            "📌 <b>Mavzuni tanlang:</b>",
            reply_markup=addq_topic_keyboard(),
            parse_mode="HTML"
        )
        await state.set_state(AdminStates.add_subcategory)

    elif category == 'sinf':
        await callback.message.edit_text(
            "🏫 <b>Sinfni tanlang:</b>",
            reply_markup=addq_grade_keyboard(),
            parse_mode="HTML"
        )
        await state.set_state(AdminStates.add_subcategory)

    elif category == 'attestation':
        # Atestatsiya — subcategory yo'q, difficulty yo'q
        await state.update_data(subcategory=None, difficulty=None, is_attestation=True)
        # order_num so'rash
        cnt = await count_questions(subject=subject, is_attestation=True)
        await callback.message.edit_text(
            f"🎓 <b>Atestatsiya savoli</b>\n\n"
            f"Hozir {cnt} ta atestatsiya savoli bor.\n"
            f"Tartib raqamini yozing (masalan: <code>{cnt + 1}</code>):",
            parse_mode="HTML"
        )
        await state.set_state(AdminStates.add_order_num)

    else:
        # aralash, gazallar — qiyinlik kerak
        await callback.message.edit_text(
            "🎯 <b>Qiyinlik darajasini tanlang:</b>",
            reply_markup=addq_difficulty_keyboard(),
            parse_mode="HTML"
        )
        await state.set_state(AdminStates.add_difficulty)

    await callback.answer()

# Subcategory (mavzu yoki sinf)
@router.callback_query(F.data.startswith("addq:topic:"))
async def addq_topic(callback: CallbackQuery, state: FSMContext):
    topic = callback.data.split(":")[2]
    await state.update_data(subcategory=topic, is_attestation=False)
    label = config.ONA_TILI_TOPICS.get(topic, topic)
    await callback.message.edit_text(
        f"📌 <b>{label}</b>\n\nQiyinlik darajasini tanlang:",
        reply_markup=addq_difficulty_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(AdminStates.add_difficulty)
    await callback.answer()

@router.callback_query(F.data.startswith("addq:grade:"))
async def addq_grade(callback: CallbackQuery, state: FSMContext):
    grade = callback.data.split(":")[2]
    await state.update_data(subcategory=grade, is_attestation=False)
    await callback.message.edit_text(
        f"🏫 <b>{grade}-sinf</b>\n\nQiyinlik darajasini tanlang:",
        reply_markup=addq_difficulty_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(AdminStates.add_difficulty)
    await callback.answer()

# Qiyinlik tanlash
@router.callback_query(F.data.startswith("addq:diff:"))
async def addq_difficulty(callback: CallbackQuery, state: FSMContext):
    difficulty = callback.data.split(":")[2]
    await state.update_data(difficulty=difficulty, is_attestation=False)
    DIFF = {'easy': '🟢 Oson', 'medium': "🟡 O'rta", 'hard': '🔴 Qiyin'}
    await callback.message.edit_text(
        f"✅ Qiyinlik: <b>{DIFF.get(difficulty)}</b>\n\n"
        f"📸 Savol rasmini yuboring yoki o'tkazib yuboring:",
        parse_mode="HTML",
    )
    await callback.message.answer(
        "📸 Rasm yuboring yoki o'tkazib yuboring:",
        reply_markup=skip_image_keyboard()
    )
    await state.set_state(AdminStates.add_image)
    await callback.answer()

# Order num (attestation uchun)
@router.message(AdminStates.add_order_num)
async def addq_order_num(message: Message, state: FSMContext):
    try:
        order_num = int(message.text.strip())
        await state.update_data(order_num=order_num)
    except ValueError:
        await message.answer("❌ Raqam kiriting!")
        return

    await message.answer(
        "📸 Rasm yuboring yoki o'tkazib yuboring:",
        reply_markup=skip_image_keyboard()
    )
    await state.set_state(AdminStates.add_image)

# Rasm
@router.message(AdminStates.add_image, F.photo)
async def addq_image(message: Message, state: FSMContext):
    await state.update_data(image_file_id=message.photo[-1].file_id)
    await message.answer(
        "✅ Rasm saqlandi.\n\n📝 Savol matnini yozing:",
        reply_markup=cancel_keyboard()
    )
    await state.set_state(AdminStates.add_text)

@router.message(AdminStates.add_image, F.text == "⏭ Rasmisiz davom etish")
async def addq_skip_image(message: Message, state: FSMContext):
    await state.update_data(image_file_id=None)
    await message.answer("📝 Savol matnini yozing:", reply_markup=cancel_keyboard())
    await state.set_state(AdminStates.add_text)

# Savol matni
@router.message(AdminStates.add_text)
async def addq_text(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("❌ Bekor qilindi.", reply_markup=admin_keyboard())
        return
    await state.update_data(question_text=message.text)
    await message.answer("🅰 A variantini yozing:")
    await state.set_state(AdminStates.add_a)

# Variantlar
@router.message(AdminStates.add_a)
async def addq_a(message: Message, state: FSMContext):
    await state.update_data(option_a=message.text)
    await message.answer("🅱 B variantini yozing:")
    await state.set_state(AdminStates.add_b)

@router.message(AdminStates.add_b)
async def addq_b(message: Message, state: FSMContext):
    await state.update_data(option_b=message.text)
    await message.answer("🅲 C variantini yozing:")
    await state.set_state(AdminStates.add_c)

@router.message(AdminStates.add_c)
async def addq_c(message: Message, state: FSMContext):
    await state.update_data(option_c=message.text)
    await message.answer("🅳 D variantini yozing:")
    await state.set_state(AdminStates.add_d)

@router.message(AdminStates.add_d)
async def addq_d(message: Message, state: FSMContext):
    await state.update_data(option_d=message.text)
    await message.answer(
        "✅ <b>To'g'ri javobni tanlang:</b>",
        reply_markup=correct_answer_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(AdminStates.add_correct)

# To'g'ri javob
@router.callback_query(F.data.startswith("addq:correct:"))
async def addq_correct(callback: CallbackQuery, state: FSMContext):
    correct = callback.data.split(":")[2]
    data    = await state.get_data()
    await state.clear()

    await add_question(
        subject        = data['subject'],
        category       = data['category'],
        question_text  = data['question_text'],
        option_a       = data['option_a'],
        option_b       = data['option_b'],
        option_c       = data['option_c'],
        option_d       = data['option_d'],
        correct_answer = correct,
        subcategory    = data.get('subcategory'),
        difficulty     = data.get('difficulty'),
        is_attestation = data.get('is_attestation', False),
        order_num      = data.get('order_num'),
        image_file_id  = data.get('image_file_id'),
    )

    SUBJ = {'onatili': '📚 Ona tili', 'adabiyot': '📖 Adabiyot'}
    await callback.message.edit_text(
        f"✅ <b>Savol muvaffaqiyatli qo'shildi!</b>\n\n"
        f"📚 Fan: {SUBJ.get(data['subject'])}\n"
        f"📁 Kategoriya: {data['category']}\n"
        f"🔑 Subcategory: {data.get('subcategory') or '—'}\n"
        f"🎯 Qiyinlik: {data.get('difficulty') or '—'}\n"
        f"✅ To'g'ri javob: <b>{correct}</b>",
        parse_mode="HTML"
    )
    await callback.message.answer(
        "Yana savol qo'shish uchun '➕ Savol qo'shish' tugmasini bosing.",
        reply_markup=admin_keyboard()
    )
    await callback.answer()

# Bekor qilish callback
@router.callback_query(F.data == "addq:cancel")
async def addq_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Bekor qilindi.")
    await callback.message.answer("Admin panel:", reply_markup=admin_keyboard())
    await callback.answer()