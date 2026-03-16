import html
import io
import openpyxl
from aiogram import Router, F, Bot
from aiogram.types import Message, BufferedInputFile
from aiogram.fsm.context import FSMContext

from database.db import (
    get_all_users, get_full_stats, add_question,
    count_questions, delete_all_questions
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
    SUBJ = {
        'onatili':     '📚 Ona tili',
        'adabiyot':    '📖 Adabiyot',
        'attestation': '🎓 Attestatsiya',
        'milliy':      '🏅 Milliy sertifikat',
    }
    if subject in ('attestation', 'milliy'):
        await state.update_data(category=subject, subcategory=None, is_attestation=True)
        await callback.message.edit_text(
            f"📁 <b>{SUBJ.get(subject)}</b>\n\nSavol turini tanlang:",
            reply_markup=addq_category_keyboard(subject),
            parse_mode="HTML"
        )
        await state.set_state(AdminStates.add_is_attest)
    else:
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

    else:
        # aralash, gazallar, sheriy, badiiy — to'g'ridan rasmga
        await state.update_data(is_attestation=False, subcategory=None)
        await callback.message.answer(
            "📸 Rasm yuboring yoki o'tkazib yuboring:",
            reply_markup=skip_image_keyboard()
        )
        await state.set_state(AdminStates.add_image)

    await callback.answer()

# Subcategory (mavzu yoki sinf)
@router.callback_query(F.data.startswith("addq:topic:"))
async def addq_topic(callback: CallbackQuery, state: FSMContext):
    topic = callback.data.split(":")[2]
    await state.update_data(subcategory=topic, is_attestation=False)
    label = config.ONA_TILI_BOLIMLAR.get(topic, topic)
    await callback.message.answer(
        f"📌 <b>{label}</b>\n\n📸 Rasm yuboring yoki o'tkazib yuboring:",
        reply_markup=skip_image_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(AdminStates.add_image)
    await callback.answer()

@router.callback_query(F.data.startswith("addq:grade:"))
async def addq_grade(callback: CallbackQuery, state: FSMContext):
    grade = callback.data.split(":")[2]
    await state.update_data(subcategory=grade, is_attestation=False)
    await callback.message.answer(
        f"🏫 <b>{grade}-sinf</b>\n\n📸 Rasm yuboring yoki o'tkazib yuboring:",
        reply_markup=skip_image_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(AdminStates.add_image)
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

# Savol turi tanlash (attestation/milliy uchun)
@router.callback_query(F.data.startswith("addq:qtype:"))
async def addq_qtype(callback: CallbackQuery, state: FSMContext):
    qtype   = callback.data.split(":")[2]
    data    = await state.get_data()
    subject = data.get('subject', 'onatili')
    LABELS  = {'attestation': '🎓 Attestatsiya', 'milliy': '🏅 Milliy sertifikat'}
    label   = LABELS.get(subject, subject)

    if qtype == 'choice':
        await state.update_data(question_type='choice', written_parts=1)
        cnt = await count_questions(subject=subject, category=subject, is_attestation=True)
        await callback.message.edit_text(
            f"{label} — Variantli savol\n\nTartib raqamini yozing (<code>{cnt + 1}</code>):",
            parse_mode="HTML"
        )
        await state.set_state(AdminStates.add_order_num)
    elif qtype in ('written1', 'written2'):
        parts = 1 if qtype == 'written1' else 2
        await state.update_data(question_type='written', written_parts=parts)
        cnt = await count_questions(subject=subject, category=subject, is_attestation=True)
        await callback.message.edit_text(
            f"{label} — Yozma savol ({parts} qism)\n\nTartib raqamini yozing (<code>{cnt + 1}</code>):",
            parse_mode="HTML"
        )
        await state.set_state(AdminStates.add_order_num)
    await callback.answer()

# To'g'ri javob
@router.callback_query(F.data.startswith("addq:correct:"))
async def addq_correct(callback: CallbackQuery, state: FSMContext):
    correct = callback.data.split(":")[2]
    data    = await state.get_data()
    await state.clear()

    subj = data['subject']
    cat  = data.get('category', subj)  # attestation/milliy uchun category=subject

    await add_question(
        subject        = subj,
        category       = cat,
        question_text  = data['question_text'],
        option_a       = data.get('option_a'),
        option_b       = data.get('option_b'),
        option_c       = data.get('option_c'),
        option_d       = data.get('option_d'),
        correct_answer = correct,
        subcategory    = data.get('subcategory'),
        difficulty     = None,
        is_attestation = data.get('is_attestation', False),
        order_num      = data.get('order_num'),
        image_file_id  = data.get('image_file_id'),
        question_type  = data.get('question_type', 'choice'),
        written_parts  = data.get('written_parts', 1),
    )

    SUBJ = {'onatili': '📚 Ona tili', 'adabiyot': '📖 Adabiyot',
             'attestation': '🎓 Attestatsiya', 'milliy': '🏅 Milliy sertifikat'}
    await callback.message.edit_text(
        f"✅ <b>Savol qo'shildi!</b>\n\n"
        f"📚 {SUBJ.get(subj, subj)} | {cat}\n"
        f"🔑 Subcategory: {data.get('subcategory') or '—'}\n"
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

# ══════════════════════════════════════════════
# BARCHA SAVOLLARNI O'CHIRISH
# ══════════════════════════════════════════════

@router.message(F.text == "🗑 Savollarni o'chirish")
async def delete_questions_confirm(message: Message):
    if not is_admin(message): return
    cnt = await count_questions()
    await message.answer(
        f"⚠️ <b>Diqqat!</b>\n\n"
        f"Hozir bazada <b>{cnt} ta</b> savol bor.\n"
        f"Barchasini o'chirishni tasdiqlaysizmi?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🗑 Ha, o'chirish", callback_data="admin:delete_all_q"),
                InlineKeyboardButton(text="❌ Yo'q", callback_data="admin:cancel_delete"),
            ]
        ]),
        parse_mode="HTML"
    )

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

@router.callback_query(F.data == "admin:delete_all_q")
async def delete_questions_execute(callback: CallbackQuery):
    deleted = await delete_all_questions()
    await callback.message.edit_text(
        f"🗑 <b>{deleted} ta savol o'chirildi!</b>",
        parse_mode="HTML"
    )
    await callback.message.answer("Admin panel:", reply_markup=admin_keyboard())
    await callback.answer()

@router.callback_query(F.data == "admin:cancel_delete")
async def delete_questions_cancel(callback: CallbackQuery):
    await callback.message.edit_text("❌ Bekor qilindi.")
    await callback.answer()

# ══════════════════════════════════════════════
# YECHIM LINKI
# ══════════════════════════════════════════════

@router.message(F.text == "🔗 Yechim linki")
async def solution_url_info(message: Message):
    if not is_admin(message): return
    url = config.SOLUTION_URL
    if url:
        await message.answer(
            f"🔗 <b>Hozirgi yechim linki:</b>\n<code>{url}</code>\n\n"
            f"O'zgartirish uchun .env faylida <code>SOLUTION_URL</code> ni yangilang.",
            parse_mode="HTML"
        )
    else:
        await message.answer(
            "⚠️ <b>SOLUTION_URL</b> .env faylida yo'q!\n\n"
            "Qo'shish uchun:\n<code>SOLUTION_URL=https://t.me/kanal_nomi</code>",
            parse_mode="HTML"
        )

# ══════════════════════════════════════════════
# EXCEL DAN KO'P SAVOL YUKLASH
# ══════════════════════════════════════════════

@router.message(F.text == "📤 Excel import")
async def excel_import_start(message: Message):
    if not is_admin(message): return

    from openpyxl.styles import Font, PatternFill, Alignment
    from openpyxl.utils import get_column_letter

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Savollar"

    headers = ["subject", "category", "subcategory",
               "is_attestation", "order_num", "question",
               "a", "b", "c", "d", "correct",
               "question_type", "written_parts", "keywords_1", "keywords_2"]

    hfill   = PatternFill("solid", fgColor="1F4E79")
    hfill_w = PatternFill("solid", fgColor="7B2D8B")
    hfont   = Font(bold=True, color="FFFFFF", size=11)

    for i, h in enumerate(headers, 1):
        cell = ws.cell(1, i)
        cell.value = h
        cell.font  = hfont
        cell.fill  = hfill_w if i >= 12 else hfill
        cell.alignment = Alignment(horizontal='center')

    widths = [12, 14, 30, 14, 10, 50, 20, 20, 20, 20, 10, 14, 14, 30, 30]
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w

    fill_ona   = PatternFill("solid", fgColor="EBF3FB")
    fill_ada   = PatternFill("solid", fgColor="EBF7EE")
    fill_att   = PatternFill("solid", fgColor="FFF2CC")
    fill_mil_v = PatternFill("solid", fgColor="E8F5E9")
    fill_mil_w = PatternFill("solid", fgColor="FCE4EC")

    # subject, category, subcategory, is_att, order, question, a,b,c,d, correct, qtype, parts, kw1, kw2
    examples = [
        # Ona tili — oddiy savollar
        ["onatili", "mavzu", "fonetika_tovushlar_tasnifi", "FALSE", None,
         "O'zbek tilida nechta unli tovush bor?", "5 ta", "6 ta", "7 ta", "8 ta", "B",
         "choice", 1, None, None],
        ["onatili", "mavzu", "morfologiya_m_ot", "FALSE", None,
         "Qaysi so'z ot turkumiga kiradi?", "yugurmoq", "baland", "maktab", "tez", "C",
         "choice", 1, None, None],
        ["onatili", "aralash", None, "FALSE", None,
         "Sintaksis nimani o'rganadi?", "So'z yasalishini", "Gap qurilishini", "Tovushlarni", "So'z ma'nosini", "B",
         "choice", 1, None, None],
        # Adabiyot — oddiy savollar
        ["adabiyot", "sinf", "7_2", "FALSE", None,
         "Navoiy qaysi asrda yashagan?", "XIV asr", "XV asr", "XVI asr", "XIII asr", "B",
         "choice", 1, None, None],
        ["adabiyot", "sheriy", None, "FALSE", None,
         "Tashbeh nima?", "O'xshatish", "Mubolag'a", "Takror", "Irsoli masal", "A",
         "choice", 1, None, None],
        # Attestatsiya — subject="attestation", 1-35 variantli, fan ajratilmaydi
        ["attestation", "attestation", None, "TRUE", 1,
         "Fonetika nimani o'rganadi?", "So'z ma'nosini", "Tovush va harflarni", "Gap tuzilishini", "So'z yasalishini", "B",
         "choice", 1, None, None],
        ["attestation", "attestation", None, "TRUE", 2,
         "Navoiy qaysi asrda yashagan?", "XIV asr", "XV asr", "XVI asr", "XIII asr", "B",
         "choice", 1, None, None],
        # Milliy sertifikat — subject="milliy", variantli (1-35)
        ["milliy", "milliy", None, "TRUE", 1,
         "Fonetika nimani o'rganadi?", "So'z ma'nosini", "Tovush va harflarni", "Gap tuzilishini", "So'z yasalishini", "B",
         "choice", 1, None, None],
        ["milliy", "milliy", None, "TRUE", 2,
         "Navoiy qaysi asrda yashagan?", "XIV asr", "XV asr", "XVI asr", "XIII asr", "B",
         "choice", 1, None, None],
        # Milliy sertifikat — yozma 1 qism (36-38)
        ["milliy", "milliy", None, "TRUE", 36,
         "Fonetika fanining asosiy vazifasini izohlang.", None, None, None, None, None,
         "written", 1, "tovush, harflar, talaffuz", None],
        ["milliy", "milliy", None, "TRUE", 37,
         "Navoiy ijodining asosiy mavzusini tushuntiring.", None, None, None, None, None,
         "written", 1, "inson, muhabbat, ma'rifat", None],
        # Milliy sertifikat — yozma 2 qism (39-44)
        ["milliy", "milliy", None, "TRUE", 39,
         "Ot so'z turkumini ta'riflang va misol keltiring.", None, None, None, None, None,
         "written", 2, "ot, predmet, kim, nima", "misol, qo'shimcha"],
        ["milliy", "milliy", None, "TRUE", 40,
         "G'azal janrining xususiyatlarini izohlang.", None, None, None, None, None,
         "written", 2, "g'azal, bayt, radif, qofiya", "misol, Navoiy"],
    ]

    for i, row_data in enumerate(examples, start=2):
        subj     = row_data[0]
        is_yazma = len(row_data) > 11 and row_data[11] == "written"
        if subj == "milliy" and is_yazma:
            fill = fill_mil_w
        elif subj == "milliy":
            fill = fill_mil_v
        elif subj == "attestation":
            fill = fill_att
        elif subj == "onatili":
            fill = fill_ona
        else:
            fill = fill_ada
        for j, val in enumerate(row_data, start=1):
            cell = ws.cell(i, j)
            cell.value = val
            cell.fill  = fill

    # Qo'llanma
    ws2 = wb.create_sheet("Qo'llanma")
    ws2.column_dimensions['A'].width = 36
    ws2.column_dimensions['B'].width = 60

    hf2    = PatternFill("solid", fgColor="1F4E79")
    hfont2 = Font(bold=True, color="FFFFFF")
    blue   = Font(bold=True, color="1F4E79")
    red    = Font(bold=True, color="C00000")
    bold   = Font(bold=True)

    guide = [
        ("SAVOLLAR SHABLONI — ONA TILI VA ADABIYOT BOTI", ""),
        ("", ""),
        ("USTUN", "QIYMAT / IZOH"),
        ("subject",        "onatili | adabiyot | attestation | milliy"),
        ("category",       "mavzu | aralash | sinf | gazallar | sheriy | badiiy | attestation | milliy"),
        ("subcategory",    "Pastdagi jadvalga qarang"),
        ("is_attestation", "FALSE  (attestation/milliy uchun TRUE)"),
        ("order_num",      "Attestation: 1-35 | Milliy: 1-35 variantli, 36-38 yozma(1q), 39-44 yozma(2q)"),
        ("question",       "Savol matni"),
        ("a / b / c / d",  "Variant matni  (yozma savol uchun bo'sh qoldiring)"),
        ("correct",        "To'g'ri javob: A|B|C|D  (yozma savol uchun bo'sh)"),
        ("question_type",  "choice  |  written"),
        ("written_parts",  "1  yoki  2"),
        ("keywords_1",     "1-qism kalit so'zlari — vergul bilan: fonetika, tovush, unli"),
        ("keywords_2",     "2-qism kalit so'zlari — faqat written_parts=2 bo'lsa"),
        ("", ""),
        ("ESLATMA: difficulty ustuni yo'q!", ""),
        ("", ""),
        ("ATTESTATSIYA", "subject=attestation, category=attestation, fan ajratilmaydi, faqat 1-35 variantli"),
        ("MILLIY SERTIFIKAT", "subject=milliy, category=milliy, fan ajratilmaydi"),
        ("  1-35 savol",  "question_type=choice"),
        ("  36-38 savol", "question_type=written, written_parts=1"),
        ("  39-44 savol", "question_type=written, written_parts=2"),
        ("", ""),
        ("ONA TILI — SUBCATEGORY", ""),
        ("category = mavzu", ""),
        ("fonetika",                    "Fonetika (barcha)"),
        ("fonetika_tovushlar_tasnifi",  "Tovushlar tasnifi"),
        ("fonetika_tovush_ozgarishi",   "Tovush o'zgarishlari"),
        ("imlo",                        "Imlo (barcha)"),
        ("imlo_togri_yozilgan",         "Qaysi so'z to'g'ri yozilgan"),
        ("imlo_imloviy_xato",           "Gapda imloviy xato"),
        ("morfemika",                   "Morfemika (barcha)"),
        ("morfemika_qoshimchalar",      "Qo'shimchalar tasnifi"),
        ("morfemika_tub_yasama",        "Tub va yasama so'zlar"),
        ("leksikologiya",               "Leksikologiya (barcha)"),
        ("leksikologiya_oz_kochma",     "O'z va ko'chma ma'no"),
        ("leksikologiya_omonimlik",     "Omonimlik"),
        ("leksikologiya_paronimlik",    "Paronimlik"),
        ("leksikologiya_ibora",         "Ibora va tasviriy ifodalar"),
        ("leksikologiya_lugatlar",      "Lug'atlardan"),
        ("morfologiya_m",               "Morfologiya mustaqil (barcha)"),
        ("morfologiya_m_ot",            "Ot"), ("morfologiya_m_sifat", "Sifat"),
        ("morfologiya_m_son",           "Son"), ("morfologiya_m_olmosh", "Olmosh"),
        ("morfologiya_m_ravish",        "Ravish"), ("morfologiya_m_fel", "Fe'l"),
        ("morfologiya_y",               "Morfologiya yordamchi (barcha)"),
        ("morfologiya_y_boglovchilar",  "Bog'lovchilar"),
        ("morfologiya_y_komakchilar",   "Ko'makchilar"),
        ("morfologiya_y_yuklamalar",    "Yuklamalar"),
        ("morfologiya_a",               "Alohida so'z turkumlari"),
        ("sintaksis",                   "Sintaksis (barcha)"),
        ("sintaksis_sozlar_boglashi",   "So'zlarning bog'lanishi"),
        ("sintaksis_gap_bolaklari",     "Gap bo'laklari"),
        ("sintaksis_qoshma_gaplar",     "Qo'shma gaplar"),
        ("matnlar",                     "Matnlar (barcha)"),
        ("matnlar_ilmiy_matn",          "Ilmiy matnlar"),
        ("matnlar_badiiy_matn",         "Badiiy matnlar"),
        ("punktuatsiya",                "Punktuatsiya"),
        ("uslubiyat",                   "Uslubiyat (barcha)"),
        ("uslubiyat_qoshimchalar_uslubiyat", "Qo'shimchalar uslubiyati"),
        ("uslubiyat_sozlar_uslubiyat",  "So'zlar uslubiyati"),
        ("category = aralash",          "subcategory = bo'sh"),
        ("", ""),
        ("ADABIYOT — SUBCATEGORY", ""),
        ("category = sinf", ""),
        ("5 / 5_1 / 5_2 / 5_3 / 5_4",  "5-sinf barcha / bob bo'yicha"),
        ("6...10 uchun ham xuddi shunday", ""),
        ("11 / 11_1 / 11_2 / 11_3 / 11_4", "11-sinf"),
        ("category = gazallar",  "subcategory = bo'sh"),
        ("category = sheriy",    "subcategory = bo'sh"),
        ("category = badiiy",    "subcategory = bo'sh"),
        ("category = aralash",   "subcategory = bo'sh"),
    ]

    for i, (col_a, col_b) in enumerate(guide, start=1):
        ca = ws2.cell(i, 1, col_a)
        cb = ws2.cell(i, 2, col_b)
        if i == 1:
            ca.font = Font(bold=True, size=13, color="1F4E79")
        elif col_a == "USTUN":
            ca.fill = hf2; ca.font = hfont2
            cb.fill = hf2; cb.font = hfont2
        elif col_a in ("ONA TILI — SUBCATEGORY", "ADABIYOT — SUBCATEGORY",
                       "ATTESTATSIYA", "MILLIY SERTIFIKAT"):
            ca.font = blue
        elif "ESLATMA" in col_a:
            ca.font = red
        elif col_a.startswith("category ="):
            ca.font = bold
        ca.alignment = Alignment(wrap_text=True, vertical='top')
        cb.alignment = Alignment(wrap_text=True, vertical='top')

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)

    await message.answer_document(
        document=BufferedInputFile(buf.read(), filename="savollar_shablon.xlsx"),
        caption=(
            "📋 <b>Excel shablon</b>\n\n"
            "🔵 Ona tili savollar\n"
            "🟢 Adabiyot savollar\n"
            "🟡 Attestatsiya (1-35 variantli, fan ajratilmaydi)\n"
            "🟩 Milliy sertifikat variantli (1-35)\n"
            "🩷 Milliy sertifikat yozma (36-44)\n\n"
            "1️⃣ Yuklab oling  2️⃣ To'ldiring  3️⃣ Yuboring\n"
            "📌 <b>Qo'llanma</b> varaqasini o'qing!"
        ),
        parse_mode="HTML"
    )
@router.message(F.document)
async def excel_import_upload(message: Message):
    if not is_admin(message): return

    doc = message.document
    if not doc.file_name or not doc.file_name.endswith('.xlsx'):
        return  # xlsx emas — e'tiborsiz

    await message.answer("⏳ Fayl o'qilmoqda...")

    # Faylni yuklab olish
    from aiogram import Bot
    bot: Bot = message.bot
    file = await bot.get_file(doc.file_id)
    buf = io.BytesIO()
    await bot.download_file(file.file_path, buf)
    buf.seek(0)

    wb = openpyxl.load_workbook(buf)
    ws = wb.active

    VALID_SUBJECTS   = {'onatili', 'adabiyot', 'attestation', 'milliy'}
    VALID_CATEGORIES = {'mavzu', 'aralash', 'sinf', 'gazallar',
                        'sheriy', 'badiiy', 'attestation', 'milliy'}
    VALID_CORRECT    = {'A', 'B', 'C', 'D'}

    added   = 0
    skipped = 0
    errors  = []

    # Format aniqlash — sarlavhaga qarab
    first_row = next(ws.iter_rows(min_row=1, max_row=1, values_only=True), None)
    cols = [str(c or '').strip().lower() for c in (first_row or [])]
    has_difficulty   = 'difficulty' in cols
    has_written_cols = 'question_type' in cols

    for row_num, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        if not row or not any(row):
            continue

        try:
            if has_difficulty:
                # Eski format (12 ustun)
                subject        = str(row[0] or '').strip().lower()
                category       = str(row[1] or '').strip().lower()
                subcategory    = str(row[2] or '').strip() or None
                is_attestation = str(row[4] or '').strip().upper() == 'TRUE'
                order_num      = int(row[5]) if row[5] else None
                question_text  = str(row[6] or '').strip()
                option_a       = str(row[7] or '').strip() or None
                option_b       = str(row[8] or '').strip() or None
                option_c       = str(row[9] or '').strip() or None
                option_d       = str(row[10] or '').strip() or None
                correct        = str(row[11] or '').strip().upper() or None
                question_type  = 'choice'
                written_parts  = 1
                keywords_1     = None
                keywords_2     = None
            elif has_written_cols:
                # Yangi format (15 ustun)
                subject        = str(row[0] or '').strip().lower()
                category       = str(row[1] or '').strip().lower()
                subcategory    = str(row[2] or '').strip() or None
                is_attestation = str(row[3] or '').strip().upper() == 'TRUE'
                order_num      = int(row[4]) if row[4] else None
                question_text  = str(row[5] or '').strip()
                option_a       = str(row[6] or '').strip() or None
                option_b       = str(row[7] or '').strip() or None
                option_c       = str(row[8] or '').strip() or None
                option_d       = str(row[9] or '').strip() or None
                correct        = str(row[10] or '').strip().upper() or None
                question_type  = str(row[11] or 'choice').strip().lower() or 'choice'
                written_parts  = int(row[12]) if row[12] else 1
                keywords_1     = str(row[13] or '').strip() or None
                keywords_2     = str(row[14] or '').strip() or None
            else:
                # O'rta format (11 ustun)
                subject        = str(row[0] or '').strip().lower()
                category       = str(row[1] or '').strip().lower()
                subcategory    = str(row[2] or '').strip() or None
                is_attestation = str(row[3] or '').strip().upper() == 'TRUE'
                order_num      = int(row[4]) if row[4] else None
                question_text  = str(row[5] or '').strip()
                option_a       = str(row[6] or '').strip() or None
                option_b       = str(row[7] or '').strip() or None
                option_c       = str(row[8] or '').strip() or None
                option_d       = str(row[9] or '').strip() or None
                correct        = str(row[10] or '').strip().upper() or None
                question_type  = 'choice'
                written_parts  = 1
                keywords_1     = None
                keywords_2     = None

            if subject not in VALID_SUBJECTS:
                errors.append(f"Qator {row_num}: subject '{subject}' noto'g'ri")
                skipped += 1; continue
            if category not in VALID_CATEGORIES:
                errors.append(f"Qator {row_num}: category '{category}' noto'g'ri")
                skipped += 1; continue
            if not question_text:
                errors.append(f"Qator {row_num}: savol matni bo'sh")
                skipped += 1; continue
            if question_type == 'choice':
                if correct not in VALID_CORRECT:
                    errors.append(f"Qator {row_num}: correct '{correct}' noto'g'ri")
                    skipped += 1; continue
                if not all([option_a, option_b, option_c, option_d]):
                    errors.append(f"Qator {row_num}: variantlar to'liq emas")
                    skipped += 1; continue

            await add_question(
                subject=subject, category=category,
                subcategory=subcategory, difficulty=None,
                is_attestation=is_attestation, order_num=order_num,
                question_text=question_text,
                option_a=option_a, option_b=option_b,
                option_c=option_c, option_d=option_d,
                correct_answer=correct,
                question_type=question_type,
                written_parts=written_parts,
                keywords_1=keywords_1,
                keywords_2=keywords_2,
            )
            added += 1

        except Exception as e:

            errors.append(f"Qator {row_num}: {html.escape(str(e))}")
            skipped += 1

    # Natija — asosiy xabar
    text = (
        f"✅ <b>Import tugadi!</b>\n\n"
        f"✅ Qo'shildi: <b>{added} ta</b>\n"
        f"❌ O'tkazildi: <b>{skipped} ta</b>\n"
    )
    if errors:
        text += f"\n⚠️ Xatolar: <b>{len(errors)} ta</b>"

    await message.answer(text, parse_mode="HTML", reply_markup=admin_keyboard())

    # Xatolar bo'lsa — alohida xabarlarda (4096 limit)
    if errors:
        chunk = ""
        for err in errors:
            line = html.escape(str(err)) + "\n"
            if len(chunk) + len(line) > 3800:
                await message.answer(f"<code>{chunk}</code>", parse_mode="HTML")
                chunk = ""
            chunk += line
        if chunk:
            await message.answer(f"<code>{chunk}</code>", parse_mode="HTML")