from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from database.db import (
    get_questions_page, search_questions,
    get_question_by_id, update_question, delete_question,
    count_questions
)
from keyboards.keyboards import admin_keyboard, cancel_keyboard
from states import EditQuestionStates
from config import config

router = Router()

PAGE_SIZE = 5

# ══════════════════════════════════════════════
# YORDAMCHI
# ══════════════════════════════════════════════

def is_admin(user_id: int) -> bool:
    return user_id in config.ADMIN_IDS

def question_short(q) -> str:
    """Savol qisqa ko'rinishi"""
    SUBJ = {'onatili': '📚', 'adabiyot': '📖'}
    DIFF = {'easy': '🟢', 'medium': '🟡', 'hard': '🔴'}
    icon   = SUBJ.get(q.subject, '❓')
    diff   = DIFF.get(q.difficulty or '', '')
    attest = "🎓" if q.is_attestation else ''
    sub    = f"[{q.subcategory}]" if q.subcategory else ''
    text   = q.question_text[:50] + ('…' if len(q.question_text) > 50 else '')
    return f"{icon}{diff}{attest} #{q.id} {sub}\n{text}"

def question_full(q) -> str:
    """Savol to'liq ko'rinishi"""
    SUBJ = {'onatili': '📚 Ona tili', 'adabiyot': '📖 Adabiyot'}
    DIFF = {'easy': '🟢 Oson', 'medium': "🟡 O'rta", 'hard': '🔴 Qiyin'}
    ans  = {'A': '🅰', 'B': '🅱', 'C': '🅲', 'D': '🅳'}

    lines = [
        f"🆔 ID: <b>{q.id}</b>",
        f"📚 Fan: <b>{SUBJ.get(q.subject, q.subject)}</b>",
        f"📁 Kategoriya: <b>{q.category}</b>",
    ]
    if q.subcategory:
        lines.append(f"📌 Subcategory: <b>{q.subcategory}</b>")
    if q.difficulty:
        lines.append(f"🎯 Qiyinlik: <b>{DIFF.get(q.difficulty, q.difficulty)}</b>")
    if q.is_attestation:
        lines.append(f"🎓 Atestatsiya | Tartib: <b>{q.order_num}</b>")
    lines += [
        f"\n❓ <b>Savol:</b>\n{q.question_text}",
        f"\n🅰 {q.option_a}",
        f"🅱 {q.option_b}",
        f"🅲 {q.option_c}",
        f"🅳 {q.option_d}",
        f"\n✅ To'g'ri: <b>{ans.get(q.correct_answer, '')} {q.correct_answer}</b>",
    ]
    if q.image_file_id:
        lines.append("🖼 Rasm: bor")
    return "\n".join(lines)

def page_keyboard(questions: list, page: int, total: int, prefix: str) -> InlineKeyboardMarkup:
    """Sahifalash klaviaturasi"""
    buttons = []

    # Savollar ro'yxati
    for q in questions:
        DIFF = {'easy': '🟢', 'medium': '🟡', 'hard': '🔴'}
        diff = DIFF.get(q.difficulty or '', '')
        attest = "🎓" if q.is_attestation else ''
        label = f"{diff}{attest} #{q.id} — {q.question_text[:30]}…"
        buttons.append([InlineKeyboardButton(
            text=label,
            callback_data=f"qedit:view:{q.id}:{page}:{prefix}"
        )])

    # Navigatsiya
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀️ Oldingi", callback_data=f"qedit:page:{page-1}:{prefix}"))
    total_pages = (total + PAGE_SIZE - 1) // PAGE_SIZE
    nav.append(InlineKeyboardButton(text=f"{page+1}/{total_pages}", callback_data="qedit:noop"))
    if (page + 1) * PAGE_SIZE < total:
        nav.append(InlineKeyboardButton(text="Keyingi ▶️", callback_data=f"qedit:page:{page+1}:{prefix}"))
    if nav:
        buttons.append(nav)

    # Qidirish va chiqish
    buttons.append([
        InlineKeyboardButton(text="🔍 Qidirish", callback_data="qedit:search"),
        InlineKeyboardButton(text="❌ Yopish",   callback_data="qedit:close"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def question_action_keyboard(qid: int, page: int, prefix: str) -> InlineKeyboardMarkup:
    """Savol ko'rishda amallar"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✏️ Tahrirlash", callback_data=f"qedit:edit:{qid}:{page}:{prefix}"),
            InlineKeyboardButton(text="🗑 O'chirish",  callback_data=f"qedit:del:{qid}:{page}:{prefix}"),
        ],
        [InlineKeyboardButton(text="🔙 Orqaga",        callback_data=f"qedit:page:{page}:{prefix}")],
    ])

def edit_field_keyboard(qid: int, page: int, prefix: str) -> InlineKeyboardMarkup:
    """Qaysi maydonni tahrirlash"""
    fields = [
        ("question_text", "📝 Savol matni"),
        ("option_a",      "🅰 A varianti"),
        ("option_b",      "🅱 B varianti"),
        ("option_c",      "🅲 C varianti"),
        ("option_d",      "🅳 D varianti"),
        ("correct_answer","✅ To'g'ri javob"),
        ("difficulty",    "🎯 Qiyinlik"),
        ("subcategory",   "📌 Subcategory"),
        ("order_num",     "🔢 Tartib raqami"),
        ("image_file_id", "🖼 Rasm ID"),
    ]
    buttons = []
    for fkey, flabel in fields:
        buttons.append([InlineKeyboardButton(
            text=flabel,
            callback_data=f"qedit:field:{fkey}:{qid}:{page}:{prefix}"
        )])
    buttons.append([InlineKeyboardButton(
        text="🔙 Orqaga",
        callback_data=f"qedit:view:{qid}:{page}:{prefix}"
    )])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# ══════════════════════════════════════════════
# SAVOLLAR RO'YXATINI OCHISH
# ══════════════════════════════════════════════

@router.message(F.text == "📋 Savollar")
async def open_question_list(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    await state.clear()
    prefix    = "all"
    questions = await get_questions_page(offset=0, limit=PAGE_SIZE)
    total     = await count_questions()

    if not questions:
        await message.answer("❌ Bazada savollar yo'q!")
        return

    await message.answer(
        f"📋 <b>Savollar bazasi</b> — jami <b>{total}</b> ta\n\n"
        f"Savolni bosib ko'ring:",
        reply_markup=page_keyboard(questions, 0, total, prefix),
        parse_mode="HTML"
    )
    await state.set_state(EditQuestionStates.browsing)

# ══════════════════════════════════════════════
# SAHIFALASH
# ══════════════════════════════════════════════

@router.callback_query(F.data.startswith("qedit:page:"))
async def turn_page(callback: CallbackQuery, state: FSMContext):
    parts  = callback.data.split(":")
    page   = int(parts[2])
    prefix = parts[3]

    # Filter
    subject  = None if prefix == "all" else prefix.split("|")[0]
    category = None if "|" not in prefix else prefix.split("|")[1]

    questions = await get_questions_page(
        subject=subject, category=category,
        offset=page * PAGE_SIZE, limit=PAGE_SIZE
    )
    total = await count_questions(subject=subject, category=category)

    await callback.message.edit_text(
        f"📋 <b>Savollar</b> — jami <b>{total}</b> ta\n\nSavolni bosib ko'ring:",
        reply_markup=page_keyboard(questions, page, total, prefix),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "qedit:noop")
async def noop(callback: CallbackQuery):
    await callback.answer()

# ══════════════════════════════════════════════
# SAVOLNI KO'RISH
# ══════════════════════════════════════════════

@router.callback_query(F.data.startswith("qedit:view:"))
async def view_question(callback: CallbackQuery):
    parts  = callback.data.split(":")
    qid    = int(parts[2])
    page   = int(parts[3])
    prefix = parts[4]

    q = await get_question_by_id(qid)
    if not q:
        await callback.answer("❌ Savol topilmadi!", show_alert=True)
        return

    text = question_full(q)

    if q.image_file_id:
        try:
            await callback.message.delete()
            await callback.message.answer_photo(
                photo=q.image_file_id,
                caption=text,
                reply_markup=question_action_keyboard(qid, page, prefix),
                parse_mode="HTML"
            )
        except Exception:
            await callback.message.edit_text(
                text,
                reply_markup=question_action_keyboard(qid, page, prefix),
                parse_mode="HTML"
            )
    else:
        await callback.message.edit_text(
            text,
            reply_markup=question_action_keyboard(qid, page, prefix),
            parse_mode="HTML"
        )
    await callback.answer()

# ══════════════════════════════════════════════
# TAHRIRLASH
# ══════════════════════════════════════════════

@router.callback_query(F.data.startswith("qedit:edit:"))
async def edit_question(callback: CallbackQuery, state: FSMContext):
    parts  = callback.data.split(":")
    qid    = int(parts[2])
    page   = int(parts[3])
    prefix = parts[4]

    await state.update_data(edit_qid=qid, edit_page=page, edit_prefix=prefix)
    await callback.message.edit_text(
        f"✏️ <b>Savol #{qid} — qaysi maydonni tahrirlaysiz?</b>",
        reply_markup=edit_field_keyboard(qid, page, prefix),
        parse_mode="HTML"
    )
    await state.set_state(EditQuestionStates.edit_field)
    await callback.answer()

@router.callback_query(F.data.startswith("qedit:field:"))
async def edit_field_chosen(callback: CallbackQuery, state: FSMContext):
    parts     = callback.data.split(":")
    field     = parts[2]
    qid       = int(parts[3])
    page      = int(parts[4])
    prefix    = parts[5]

    FIELD_NAMES = {
        "question_text": "savol matni",
        "option_a":      "A varianti",
        "option_b":      "B varianti",
        "option_c":      "C varianti",
        "option_d":      "D varianti",
        "correct_answer":"to'g'ri javob (A/B/C/D)",
        "difficulty":    "qiyinlik (easy/medium/hard)",
        "subcategory":   "subcategory",
        "order_num":     "tartib raqami (raqam)",
        "image_file_id": "rasm file_id",
    }

    await state.update_data(
        edit_qid=qid, edit_field=field,
        edit_page=page, edit_prefix=prefix
    )

    await callback.message.edit_text(
        f"✏️ <b>#{qid} — {FIELD_NAMES.get(field, field)}</b>\n\n"
        f"Yangi qiymatni yozing:",
        parse_mode="HTML"
    )
    await state.set_state(EditQuestionStates.edit_value)
    await callback.answer()

@router.message(EditQuestionStates.edit_value)
async def edit_value_received(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("❌ Bekor qilindi.", reply_markup=admin_keyboard())
        return

    data   = await state.get_data()
    qid    = data['edit_qid']
    field  = data['edit_field']
    page   = data.get('edit_page', 0)
    prefix = data.get('edit_prefix', 'all')
    value  = message.text.strip()

    # order_num uchun int
    if field == 'order_num':
        try:
            value = int(value)
        except ValueError:
            await message.answer("❌ Raqam kiriting!")
            return

    await update_question(qid, **{field: value})
    await state.clear()

    q = await get_question_by_id(qid)
    await message.answer(
        f"✅ <b>Savol #{qid} yangilandi!</b>\n\n{question_full(q)}",
        reply_markup=question_action_keyboard(qid, page, prefix),
        parse_mode="HTML"
    )

# ══════════════════════════════════════════════
# O'CHIRISH
# ══════════════════════════════════════════════

@router.callback_query(F.data.startswith("qedit:del:"))
async def delete_question_confirm(callback: CallbackQuery, state: FSMContext):
    parts  = callback.data.split(":")
    qid    = int(parts[2])
    page   = int(parts[3])
    prefix = parts[4]

    await state.update_data(del_qid=qid, del_page=page, del_prefix=prefix)
    await callback.message.edit_text(
        f"🗑 <b>Savol #{qid} ni o'chirishni tasdiqlaysizmi?</b>\n\n"
        f"⚠️ Bu amalni qaytarib bo'lmaydi!",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Ha, o'chir",  callback_data=f"qedit:delok:{qid}:{page}:{prefix}"),
                InlineKeyboardButton(text="❌ Yo'q",        callback_data=f"qedit:view:{qid}:{page}:{prefix}"),
            ]
        ]),
        parse_mode="HTML"
    )
    await state.set_state(EditQuestionStates.confirm_delete)
    await callback.answer()

@router.callback_query(F.data.startswith("qedit:delok:"))
async def delete_question_confirmed(callback: CallbackQuery, state: FSMContext):
    parts  = callback.data.split(":")
    qid    = int(parts[2])
    page   = int(parts[3])
    prefix = parts[4]

    await delete_question(qid)
    await state.clear()

    # Sahifaga qaytish
    subject  = None if prefix == "all" else prefix.split("|")[0]
    category = None if "|" not in prefix else prefix.split("|")[1]

    questions = await get_questions_page(
        subject=subject, category=category,
        offset=page * PAGE_SIZE, limit=PAGE_SIZE
    )
    total = await count_questions(subject=subject, category=category)

    await callback.message.edit_text(
        f"✅ <b>Savol #{qid} o'chirildi!</b>\n\n"
        f"📋 Savollar — jami <b>{total}</b> ta:",
        reply_markup=page_keyboard(questions, page, total, prefix),
        parse_mode="HTML"
    )
    await callback.answer("✅ O'chirildi!")

# ══════════════════════════════════════════════
# QIDIRISH
# ══════════════════════════════════════════════

@router.callback_query(F.data == "qedit:search")
async def search_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "🔍 <b>Qidirish</b>\n\nSavol matnidan kalit so'z yozing:",
        parse_mode="HTML"
    )
    await state.set_state(EditQuestionStates.searching)
    await callback.answer()

@router.message(EditQuestionStates.searching)
async def search_questions_handler(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("❌ Bekor qilindi.", reply_markup=admin_keyboard())
        return

    keyword   = message.text.strip()
    questions = await search_questions(keyword)

    if not questions:
        await message.answer(
            f"🔍 '<b>{keyword}</b>' bo'yicha hech narsa topilmadi.",
            parse_mode="HTML"
        )
        return

    await state.clear()
    prefix = f"search|{keyword}"
    total  = len(questions)

    await message.answer(
        f"🔍 '<b>{keyword}</b>' — <b>{total}</b> ta natija:",
        reply_markup=page_keyboard(questions[:PAGE_SIZE], 0, total, prefix),
        parse_mode="HTML"
    )
    await state.set_state(EditQuestionStates.browsing)

# ══════════════════════════════════════════════
# YOPISH
# ══════════════════════════════════════════════

@router.callback_query(F.data == "qedit:close")
async def close_editor(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.delete()
    await callback.message.answer("📋 Savollar muharriri yopildi.", reply_markup=admin_keyboard())
    await callback.answer()