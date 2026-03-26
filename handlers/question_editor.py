from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from database.db import (
    get_questions_page, search_questions,
    get_question_by_id, update_question, delete_question,
    count_questions
)
from keyboards.keyboards import admin_keyboard
from states import EditQuestionStates
from config import config

router   = Router()
PAGE_SIZE = 5
# Telegram callback_data max 64 char — search keyword uchun limit
MAX_SEARCH_KW = 20


def is_admin(user_id: int) -> bool:
    return user_id in config.ADMIN_IDS


def question_short(q) -> str:
    SUBJ = {'onatili': '📚', 'adabiyot': '📖',
            'attestation': '🎓', 'milliy': '🏅'}
    icon   = SUBJ.get(q.subject, '❓')
    attest = "🎓" if q.is_attestation else ''
    sub    = f"[{q.subcategory}]" if q.subcategory else ''
    text   = q.question_text[:45] + ('…' if len(q.question_text) > 45 else '')
    return f"{icon}{attest} #{q.id} {sub}\n{text}"


def question_full(q) -> str:
    SUBJ = {
        'onatili':     '📚 Ona tili',
        'adabiyot':    '📖 Adabiyot',
        'attestation': '🎓 Attestatsiya',
        'milliy':      '🏅 Milliy',
    }
    lines = [
        f"🆔 ID: <b>{q.id}</b>",
        f"📚 Fan: <b>{SUBJ.get(q.subject, q.subject)}</b>",
        f"📁 Kategoriya: <b>{q.category}</b>",
    ]
    if q.subcategory:
        lines.append(f"📌 Subcategory: <b>{q.subcategory}</b>")
    if q.difficulty:
        DIFF = {'easy': '🟢 Oson', 'medium': "🟡 O'rta", 'hard': '🔴 Qiyin'}
        lines.append(f"🎯 Qiyinlik: <b>{DIFF.get(q.difficulty, q.difficulty)}</b>")
    if q.is_attestation:
        lines.append(f"🎓 Atestatsiya | Tartib: <b>{q.order_num}</b>")

    qtype = getattr(q, 'question_type', 'choice') or 'choice'
    lines.append(f"📝 Tur: <b>{'Variantli' if qtype == 'choice' else 'Yozma'}</b>")
    lines.append(f"\n❓ <b>Savol:</b>\n{q.question_text}")

    if qtype == 'choice':
        lines += [
            f"\n🅰 {q.option_a or '—'}",
            f"🅱 {q.option_b or '—'}",
            f"🅲 {q.option_c or '—'}",
            f"🅳 {q.option_d or '—'}",
            f"\n✅ To'g'ri: <b>{q.correct_answer or '—'}</b>",
        ]
    else:
        kw1 = getattr(q, 'keywords_1', None) or '—'
        kw2 = getattr(q, 'keywords_2', None) or ''
        parts = getattr(q, 'written_parts', 1) or 1
        lines.append(f"\n🔑 Kalit so'z (1): <b>{kw1}</b>")
        if parts == 2:
            lines.append(f"🔑 Kalit so'z (2): <b>{kw2 or '—'}</b>")

    if q.image_file_id:
        lines.append("🖼 Rasm: <b>bor</b>")
    return "\n".join(lines)


def page_keyboard(questions: list, page: int, total: int,
                  prefix: str) -> InlineKeyboardMarkup:
    buttons = []
    for q in questions:
        attest = "🎓" if q.is_attestation else ''
        label  = f"{attest}#{q.id} — {q.question_text[:28]}…"
        # callback_data max 64 char: "qedit:view:1234:5:all" = 21 char — safe
        buttons.append([InlineKeyboardButton(
            text          = label,
            callback_data = f"qedit:view:{q.id}:{page}:{prefix}"
        )])

    nav          = []
    total_pages  = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    if page > 0:
        nav.append(InlineKeyboardButton(
            text="◀️", callback_data=f"qedit:page:{page-1}:{prefix}"))
    nav.append(InlineKeyboardButton(
        text=f"{page+1}/{total_pages}", callback_data="qedit:noop"))
    if (page + 1) * PAGE_SIZE < total:
        nav.append(InlineKeyboardButton(
            text="▶️", callback_data=f"qedit:page:{page+1}:{prefix}"))
    if nav:
        buttons.append(nav)

    buttons.append([
        InlineKeyboardButton(text="🔍 Qidirish", callback_data="qedit:search"),
        InlineKeyboardButton(text="❌ Yopish",    callback_data="qedit:close"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def question_action_keyboard(qid: int, page: int,
                              prefix: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="✏️ Tahrirlash",
                callback_data=f"qedit:edit:{qid}:{page}:{prefix}"),
            InlineKeyboardButton(
                text="🗑 O'chirish",
                callback_data=f"qedit:del:{qid}:{page}:{prefix}"),
        ],
        [InlineKeyboardButton(
            text="🔙 Orqaga",
            callback_data=f"qedit:page:{page}:{prefix}")],
    ])


def edit_field_keyboard(qid: int, page: int,
                        prefix: str) -> InlineKeyboardMarkup:
    fields = [
        ("question_text",  "📝 Savol matni"),
        ("option_a",       "🅰 A varianti"),
        ("option_b",       "🅱 B varianti"),
        ("option_c",       "🅲 C varianti"),
        ("option_d",       "🅳 D varianti"),
        ("correct_answer", "✅ To'g'ri javob"),
        ("subcategory",    "📌 Subcategory"),
        ("order_num",      "🔢 Tartib raqami"),
        ("image_file_id",  "🖼 Rasm ID"),
        ("keywords_1",     "🔑 Kalit so'z 1"),
        ("keywords_2",     "🔑 Kalit so'z 2"),
    ]
    buttons = []
    for fkey, flabel in fields:
        buttons.append([InlineKeyboardButton(
            text          = flabel,
            callback_data = f"qedit:field:{fkey}:{qid}:{page}:{prefix}"
        )])
    buttons.append([InlineKeyboardButton(
        text          = "🔙 Orqaga",
        callback_data = f"qedit:view:{qid}:{page}:{prefix}"
    )])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ══════════════════════════════════════════════
# OCHISH
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
        f"📋 <b>Savollar bazasi</b> — jami <b>{total}</b> ta\n\nSavolni bosib ko'ring:",
        reply_markup = page_keyboard(questions, 0, total, prefix),
        parse_mode   = "HTML"
    )
    await state.set_state(EditQuestionStates.browsing)


# ══════════════════════════════════════════════
# SAHIFALASH
# ══════════════════════════════════════════════

@router.callback_query(F.data.startswith("qedit:page:"))
async def turn_page(callback: CallbackQuery):
    parts  = callback.data.split(":")
    page   = int(parts[2])
    prefix = parts[3]

    if prefix.startswith("srch|"):
        # search|keyword — callback_data da keyword qisqartirilgan
        keyword   = prefix[5:]
        questions = await search_questions(keyword)
        total     = len(questions)
        page_qs   = questions[page * PAGE_SIZE: (page + 1) * PAGE_SIZE]
    else:
        subject  = None if prefix == "all" else prefix.split("|")[0]
        category = prefix.split("|")[1] if "|" in prefix else None
        page_qs  = await get_questions_page(
            subject=subject, category=category,
            offset=page * PAGE_SIZE, limit=PAGE_SIZE
        )
        total = await count_questions(subject=subject, category=category)

    await callback.message.edit_text(
        f"📋 <b>Savollar</b> — jami <b>{total}</b> ta\n\nSavolni bosib ko'ring:",
        reply_markup = page_keyboard(page_qs, page, total, prefix),
        parse_mode   = "HTML"
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
    kb   = question_action_keyboard(qid, page, prefix)

    if q.image_file_id:
        try:
            await callback.message.delete()
            await callback.bot.send_photo(
                chat_id      = callback.from_user.id,
                photo        = q.image_file_id,
                caption      = text,
                reply_markup = kb,
                parse_mode   = "HTML"
            )
        except Exception:
            await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    else:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
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
        reply_markup = edit_field_keyboard(qid, page, prefix),
        parse_mode   = "HTML"
    )
    await state.set_state(EditQuestionStates.edit_field)
    await callback.answer()


@router.callback_query(F.data.startswith("qedit:field:"))
async def edit_field_chosen(callback: CallbackQuery, state: FSMContext):
    parts  = callback.data.split(":")
    field  = parts[2]
    qid    = int(parts[3])
    page   = int(parts[4])
    prefix = parts[5]

    FIELD_NAMES = {
        "question_text":  "savol matni",
        "option_a":       "A varianti",
        "option_b":       "B varianti",
        "option_c":       "C varianti",
        "option_d":       "D varianti",
        "correct_answer": "to'g'ri javob (A/B/C/D)",
        "subcategory":    "subcategory",
        "order_num":      "tartib raqami (raqam)",
        "image_file_id":  "rasm file_id",
        "keywords_1":     "kalit so'z 1 (vergul bilan)",
        "keywords_2":     "kalit so'z 2 (vergul bilan)",
    }

    await state.update_data(
        edit_qid=qid, edit_field=field,
        edit_page=page, edit_prefix=prefix
    )
    await callback.message.edit_text(
        f"✏️ <b>#{qid} — {FIELD_NAMES.get(field, field)}</b>\n\nYangi qiymatni yozing:",
        parse_mode = "HTML"
    )
    await state.set_state(EditQuestionStates.edit_value)
    await callback.answer()


@router.message(EditQuestionStates.edit_value)
async def edit_value_received(message: Message, state: FSMContext):
    if message.text and "Bekor" in message.text:
        await state.clear()
        await message.answer("❌ Bekor qilindi.", reply_markup=admin_keyboard())
        return

    data   = await state.get_data()
    qid    = data['edit_qid']
    field  = data['edit_field']
    page   = data.get('edit_page', 0)
    prefix = data.get('edit_prefix', 'all')
    value  = message.text.strip() if message.text else ''

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
        reply_markup = question_action_keyboard(qid, page, prefix),
        parse_mode   = "HTML"
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
        reply_markup = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(
                text="✅ Ha, o'chir",
                callback_data=f"qedit:delok:{qid}:{page}:{prefix}"),
            InlineKeyboardButton(
                text="❌ Yo'q",
                callback_data=f"qedit:view:{qid}:{page}:{prefix}"),
        ]]),
        parse_mode = "HTML"
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

    subject  = None if prefix == "all" else prefix.split("|")[0]
    category = prefix.split("|")[1] if "|" in prefix else None

    # Page chapga siljishi mumkin
    total = await count_questions(subject=subject, category=category)
    safe_page = min(page, max(0, (total - 1) // PAGE_SIZE))

    questions = await get_questions_page(
        subject=subject, category=category,
        offset=safe_page * PAGE_SIZE, limit=PAGE_SIZE
    )
    await callback.message.edit_text(
        f"✅ <b>Savol #{qid} o'chirildi!</b>\n\n"
        f"📋 Savollar — jami <b>{total}</b> ta:",
        reply_markup = page_keyboard(questions, safe_page, total, prefix),
        parse_mode   = "HTML"
    )
    await callback.answer("✅ O'chirildi!")


# ══════════════════════════════════════════════
# QIDIRISH
# ══════════════════════════════════════════════

@router.callback_query(F.data == "qedit:search")
async def search_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "🔍 <b>Qidirish</b>\n\nSavol matnidan kalit so'z yozing:",
        parse_mode = "HTML"
    )
    await state.set_state(EditQuestionStates.searching)
    await callback.answer()


@router.message(EditQuestionStates.searching)
async def search_questions_handler(message: Message, state: FSMContext):
    if message.text and "Bekor" in message.text:
        await state.clear()
        await message.answer("❌ Bekor qilindi.", reply_markup=admin_keyboard())
        return

    keyword   = (message.text or '').strip()[:MAX_SEARCH_KW]  # 64 char limit uchun
    questions = await search_questions(keyword)

    if not questions:
        await message.answer(
            f"🔍 '<b>{keyword}</b>' bo'yicha hech narsa topilmadi.",
            parse_mode="HTML"
        )
        return

    await state.clear()
    # Prefix: "srch|keyword" — max 5+20=25 char, safe
    prefix = f"srch|{keyword}"
    total  = len(questions)

    await message.answer(
        f"🔍 '<b>{keyword}</b>' — <b>{total}</b> ta natija:",
        reply_markup = page_keyboard(questions[:PAGE_SIZE], 0, total, prefix),
        parse_mode   = "HTML"
    )
    await state.set_state(EditQuestionStates.browsing)


# ══════════════════════════════════════════════
# YOPISH
# ══════════════════════════════════════════════

@router.callback_query(F.data == "qedit:close")
async def close_editor(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    try:
        await callback.message.delete()
    except Exception:
        pass
    # callback.message.answer() crash beradi (delete dan keyin) — bot.send_message ishlatamiz
    await callback.bot.send_message(
        chat_id      = callback.from_user.id,
        text         = "📋 Savollar muharriri yopildi.",
        reply_markup = admin_keyboard()
    )
    await callback.answer()