from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from database.db import (
    get_question_by_id, update_question, delete_question,
    search_questions, get_questions_page, get_questions_count
)
from states import EditQuestionStates
from config import config

router = Router()

DIFF_LABEL = {'easy': '🟢 Oson', 'medium': "🟡 O'rta", 'hard': '🔴 Qiyin'}
PAGE_SIZE = 5

def is_admin(uid):
    return uid in config.ADMIN_IDS

def question_card(q) -> str:
    diff = DIFF_LABEL.get(q['difficulty'], q['difficulty'])
    img = "🖼 Rasm bor" if q['image_file_id'] else "📝 Rasmsiz"
    return (
        f"🆔 <b>#{q['id']}</b>  {diff}  {img}\n\n"
        f"❓ {q['question_text']}\n\n"
        f"A: {q['option_a']}\n"
        f"B: {q['option_b']}\n"
        f"C: {q['option_c']}\n"
        f"D: {q['option_d']}\n\n"
        f"✅ To'g'ri javob: <b>{q['correct_answer']}</b>"
    )

def question_action_keyboard(question_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✏️ Tahrirlash", callback_data=f"qedit:{question_id}"),
            InlineKeyboardButton(text="🗑 O'chirish", callback_data=f"qdelete:{question_id}"),
        ],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="qback")]
    ])

def edit_field_keyboard(question_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="❓ Savol matni", callback_data=f"qfield:{question_id}:question_text"),
            InlineKeyboardButton(text="🅰 A variant", callback_data=f"qfield:{question_id}:option_a"),
        ],
        [
            InlineKeyboardButton(text="🅱 B variant", callback_data=f"qfield:{question_id}:option_b"),
            InlineKeyboardButton(text="🅲 C variant", callback_data=f"qfield:{question_id}:option_c"),
        ],
        [
            InlineKeyboardButton(text="🅳 D variant", callback_data=f"qfield:{question_id}:option_d"),
            InlineKeyboardButton(text="✅ To'g'ri javob", callback_data=f"qfield:{question_id}:correct_answer"),
        ],
        [
            InlineKeyboardButton(text="🎯 Qiyinlik", callback_data=f"qfield:{question_id}:difficulty"),
            InlineKeyboardButton(text="🖼 Rasm", callback_data=f"qfield:{question_id}:image_file_id"),
        ],
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data=f"qview:{question_id}")]
    ])

def page_keyboard(offset, total, questions):
    buttons = []
    row = []
    for q in questions:
        diff = {'easy': '🟢', 'medium': '🟡', 'hard': '🔴'}.get(q['difficulty'], '⚪')
        label = f"{diff} #{q['id']}"
        row.append(InlineKeyboardButton(text=label, callback_data=f"qview:{q['id']}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    nav = []
    if offset > 0:
        nav.append(InlineKeyboardButton(text="⬅️ Oldingi", callback_data=f"qpage:{offset - PAGE_SIZE}"))
    if offset + PAGE_SIZE < total:
        nav.append(InlineKeyboardButton(text="Keyingi ➡️", callback_data=f"qpage:{offset + PAGE_SIZE}"))
    if nav:
        buttons.append(nav)

    buttons.append([
        InlineKeyboardButton(text="🔍 Qidirish", callback_data="qsearch"),
        InlineKeyboardButton(text="❌ Yopish", callback_data="qclose")
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# ============ ENTRY POINTS ============

@router.message(Command("questions"))
@router.message(F.text == "📋 Savollar")
async def questions_list(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Ruxsat yo'q!")
        return
    await show_page(message, state, offset=0)

async def show_page(message: Message, state: FSMContext, offset: int):
    total = get_questions_count()
    questions = get_questions_page(offset=offset, limit=PAGE_SIZE)
    if not questions:
        await message.answer("❌ Savollar topilmadi.")
        return
    await state.set_state(EditQuestionStates.browsing)
    await state.update_data(offset=offset)
    text = (
        f"📋 <b>Savollar ro'yxati</b>\n"
        f"Jami: <b>{total}</b> ta  |  Sahifa: {offset//PAGE_SIZE + 1}/{(total-1)//PAGE_SIZE + 1}\n\n"
        "Savolni tanlang:"
    )
    await message.answer(text, reply_markup=page_keyboard(offset, total, questions), parse_mode="HTML")

# ============ PAGINATION ============

@router.callback_query(F.data.startswith("qpage:"))
async def cb_page(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔", show_alert=True)
        return
    offset = int(callback.data.split(":")[1])
    total = get_questions_count()
    questions = get_questions_page(offset=offset, limit=PAGE_SIZE)
    await state.update_data(offset=offset)
    text = (
        f"📋 <b>Savollar ro'yxati</b>\n"
        f"Jami: <b>{total}</b> ta  |  Sahifa: {offset//PAGE_SIZE + 1}/{(total-1)//PAGE_SIZE + 1}\n\n"
        "Savolni tanlang:"
    )
    await callback.message.edit_text(text, reply_markup=page_keyboard(offset, total, questions), parse_mode="HTML")
    await callback.answer()

# ============ VIEW QUESTION ============

@router.callback_query(F.data.startswith("qview:"))
async def cb_view(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔", show_alert=True)
        return
    qid = int(callback.data.split(":")[1])
    q = get_question_by_id(qid)
    if not q:
        await callback.answer("❌ Savol topilmadi!", show_alert=True)
        return
    await state.set_state(EditQuestionStates.viewing)
    await state.update_data(current_qid=qid)

    if q['image_file_id']:
        await callback.message.answer_photo(
            photo=q['image_file_id'],
            caption=question_card(q),
            reply_markup=question_action_keyboard(qid),
            parse_mode="HTML"
        )
    else:
        await callback.message.answer(
            question_card(q),
            reply_markup=question_action_keyboard(qid),
            parse_mode="HTML"
        )
    await callback.answer()

@router.callback_query(F.data == "qback")
async def cb_back(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    offset = data.get("offset", 0)
    total = get_questions_count()
    questions = get_questions_page(offset=offset, limit=PAGE_SIZE)
    text = (
        f"📋 <b>Savollar ro'yxati</b>\n"
        f"Jami: <b>{total}</b> ta\n\nSavolni tanlang:"
    )
    await callback.message.answer(text, reply_markup=page_keyboard(offset, total, questions), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data == "qclose")
async def cb_close(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.delete()
    await callback.answer()

# ============ DELETE ============

@router.callback_query(F.data.startswith("qdelete:"))
async def cb_delete_confirm(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔", show_alert=True)
        return
    qid = int(callback.data.split(":")[1])
    q = get_question_by_id(qid)
    await state.set_state(EditQuestionStates.confirm_delete)
    await state.update_data(current_qid=qid)
    await callback.message.answer(
        f"🗑 <b>O'chirishni tasdiqlaysizmi?</b>\n\n"
        f"❓ {q['question_text'][:80]}...",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="✅ Ha, o'chir", callback_data=f"qconfirmdel:{qid}"),
            InlineKeyboardButton(text="❌ Yo'q", callback_data=f"qview:{qid}")
        ]]),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("qconfirmdel:"))
async def cb_delete_do(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔", show_alert=True)
        return
    qid = int(callback.data.split(":")[1])
    delete_question(qid)
    await state.clear()
    await callback.message.edit_text("✅ <b>Savol o'chirildi!</b>", parse_mode="HTML")
    await callback.answer("✅ O'chirildi!")

# ============ EDIT ============

@router.callback_query(F.data.startswith("qedit:"))
async def cb_edit_choose(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔", show_alert=True)
        return
    qid = int(callback.data.split(":")[1])
    await state.set_state(EditQuestionStates.edit_choose_field)
    await state.update_data(current_qid=qid)
    await callback.message.answer(
        "✏️ <b>Qaysi maydonni tahrirlaysiz?</b>",
        reply_markup=edit_field_keyboard(qid),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("qfield:"))
async def cb_edit_field(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔", show_alert=True)
        return
    _, qid, field = callback.data.split(":")
    qid = int(qid)

    field_names = {
        'question_text': 'Savol matni',
        'option_a': 'A variant',
        'option_b': 'B variant',
        'option_c': 'C variant',
        'option_d': 'D variant',
        'correct_answer': "To'g'ri javob (A/B/C/D)",
        'difficulty': 'Qiyinlik (easy/medium/hard)',
        'image_file_id': 'Rasm (rasm yuboring yoki "oq" yozing)'
    }

    await state.set_state(EditQuestionStates.edit_value)
    await state.update_data(current_qid=qid, edit_field=field)
    await callback.message.answer(
        f"✏️ <b>{field_names.get(field, field)}</b> uchun yangi qiymat yozing:",
        parse_mode="HTML"
    )
    await callback.answer()

@router.message(EditQuestionStates.edit_value)
async def process_edit_value(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    data = await state.get_data()
    qid = data['current_qid']
    field = data['edit_field']

    if field == 'image_file_id':
        if message.photo:
            value = message.photo[-1].file_id
        elif message.text and message.text.lower() == 'oq':
            value = None
        else:
            await message.answer("📸 Rasm yuboring yoki rasmni o'chirish uchun \"oq\" yozing.")
            return
    else:
        value = message.text.strip()
        if field == 'correct_answer' and value.upper() not in ['A', 'B', 'C', 'D']:
            await message.answer("❌ Faqat A, B, C yoki D yozing!")
            return
        if field == 'difficulty' and value.lower() not in ['easy', 'medium', 'hard']:
            await message.answer("❌ Faqat: easy, medium yoki hard yozing!")
            return

    kwargs = {field: value}
    update_question(qid, **kwargs)

    await state.clear()
    q = get_question_by_id(qid)
    await message.answer(
        "✅ <b>Muvaffaqiyatli yangilandi!</b>\n\n" + question_card(q),
        reply_markup=question_action_keyboard(qid),
        parse_mode="HTML"
    )

# ============ SEARCH ============

@router.callback_query(F.data == "qsearch")
async def cb_search(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔", show_alert=True)
        return
    await state.set_state(EditQuestionStates.searching)
    await callback.message.answer("🔍 Qidirish uchun kalit so'z yozing:")
    await callback.answer()

@router.message(EditQuestionStates.searching)
async def process_search(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    results = search_questions(message.text.strip())
    if not results:
        await message.answer("❌ Hech narsa topilmadi.")
        await state.clear()
        return

    total = len(results)
    buttons = []
    for q in results:
        diff = {'easy': '🟢', 'medium': '🟡', 'hard': '🔴'}.get(q['difficulty'], '⚪')
        text_short = q['question_text'][:30] + "..."
        buttons.append([InlineKeyboardButton(
            text=f"{diff} #{q['id']} — {text_short}",
            callback_data=f"qview:{q['id']}"
        )])
    buttons.append([InlineKeyboardButton(text="❌ Yopish", callback_data="qclose")])

    await state.set_state(EditQuestionStates.browsing)
    await message.answer(
        f"🔍 <b>{total} ta natija topildi:</b>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
        parse_mode="HTML"
    )