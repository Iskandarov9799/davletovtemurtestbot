from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from datetime import datetime

from database.db import (
    get_random_questions, save_test_result, get_user_results,
    is_user_paid, is_user_registered, get_leaderboard
)
from keyboards.keyboards import (
    test_answer_keyboard, main_menu_keyboard,
    start_test_keyboard, difficulty_keyboard
)
from states import TestStates

router = Router()
TOTAL_QUESTIONS = 30

DIFFICULTY_NAMES = {
    'easy': '🟢 Oson',
    'medium': '🟡 O\'rta',
    'hard': '🔴 Qiyin',
    'mixed': '🎲 Aralash'
}

def format_question(q, index, total, difficulty):
    filled = index + 1
    empty = total - filled
    bar = "▓" * filled + "░" * empty
    diff_label = DIFFICULTY_NAMES.get(difficulty, '')

    text = (
        f"📊 <b>{index+1}/{total}</b>  [{bar}]  {diff_label}\n\n"
        f"❓ <b>{q['question_text']}</b>\n\n"
        f"🅰 {q['option_a']}\n"
        f"🅱 {q['option_b']}\n"
        f"🅲 {q['option_c']}\n"
        f"🅳 {q['option_d']}"
    )
    return text

@router.message(F.text == "📝 Testni boshlash")
async def start_test_prompt(message: Message, state: FSMContext):
    if not is_user_registered(message.from_user.id):
        await message.answer("❌ Avval ro'yxatdan o'ting! /start")
        return
    if not is_user_paid(message.from_user.id):
        await message.answer(
            "❌ Test uchun to'lov qilishingiz kerak!\n💳 \"To'lov qilish\" tugmasini bosing.",
            reply_markup=main_menu_keyboard(is_paid=False)
        )
        return
    await message.answer(
        "🎯 <b>Qiyinlik darajasini tanlang:</b>",
        reply_markup=difficulty_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(TestStates.choosing_difficulty)

@router.callback_query(TestStates.choosing_difficulty, F.data.startswith("diff:"))
async def choose_difficulty(callback: CallbackQuery, state: FSMContext):
    difficulty = callback.data.split(":")[1]
    questions = get_random_questions(subject="ona_tili", count=TOTAL_QUESTIONS, difficulty=difficulty)

    if len(questions) == 0:
        await callback.answer("❌ Bu darajada savollar yo'q!", show_alert=True)
        return

    q_list = [dict(q) for q in questions]
    await state.set_data({
        "questions": q_list,
        "current_index": 0,
        "correct": 0,
        "wrong": 0,
        "difficulty": difficulty,
        "started_at": datetime.now().isoformat()
    })
    await state.set_state(TestStates.answering)
    await callback.message.delete()

    first_q = q_list[0]
    # Agar rasmli savol bo'lsa
    if first_q.get('image_file_id'):
        await callback.message.answer_photo(
            photo=first_q['image_file_id'],
            caption=format_question(first_q, 0, len(q_list), difficulty),
            reply_markup=test_answer_keyboard(0),
            parse_mode="HTML"
        )
    else:
        await callback.message.answer(
            format_question(first_q, 0, len(q_list), difficulty),
            reply_markup=test_answer_keyboard(0),
            parse_mode="HTML"
        )
    await callback.answer()

@router.callback_query(TestStates.answering, F.data.startswith("answer:"))
async def process_answer(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split(":")
    q_index = int(parts[1])
    selected = parts[2]

    data = await state.get_data()
    questions = data["questions"]
    current_index = data["current_index"]
    difficulty = data["difficulty"]

    if q_index != current_index:
        await callback.answer("⚠️ Bu savol o'tib ketgan!", show_alert=True)
        return

    current_q = questions[current_index]
    correct_answer = current_q["correct_answer"]
    is_correct = selected == correct_answer

    correct = data["correct"] + (1 if is_correct else 0)
    wrong = data["wrong"] + (0 if is_correct else 1)

    option_map = {
        "A": current_q["option_a"], "B": current_q["option_b"],
        "C": current_q["option_c"], "D": current_q["option_d"]
    }

    if is_correct:
        result_text = "✅ <b>To'g'ri!</b>"
    else:
        result_text = (
            "❌ <b>Noto'g'ri!</b>\n"
            f"To'g'ri javob: <b>{correct_answer}) {option_map[correct_answer]}</b>"
        )

    next_index = current_index + 1
    total = len(questions)

    # Joriy savolga natija ko'rsat
    try:
        if current_q.get('image_file_id'):
            await callback.message.edit_caption(
                caption=format_question(current_q, current_index, total, difficulty) + f"\n\n{result_text}",
                parse_mode="HTML"
            )
        else:
            await callback.message.edit_text(
                format_question(current_q, current_index, total, difficulty) + f"\n\n{result_text}",
                parse_mode="HTML"
            )
    except Exception:
        pass

    if next_index >= total:
        await state.update_data(correct=correct, wrong=wrong)
        await finish_test(callback, state, correct, wrong, data["started_at"], difficulty, total)
        await callback.answer()
        return

    await state.update_data(current_index=next_index, correct=correct, wrong=wrong)

    next_q = questions[next_index]
    if next_q.get('image_file_id'):
        await callback.message.answer_photo(
            photo=next_q['image_file_id'],
            caption=format_question(next_q, next_index, total, difficulty),
            reply_markup=test_answer_keyboard(next_index),
            parse_mode="HTML"
        )
    else:
        await callback.message.answer(
            format_question(next_q, next_index, total, difficulty),
            reply_markup=test_answer_keyboard(next_index),
            parse_mode="HTML"
        )
    await callback.answer()

async def finish_test(callback, state, correct, wrong, started_at, difficulty, total):
    score = round((correct / total) * 100, 1)

    if score >= 90:
        grade, emoji = "🏆 A'lo (5)", "🎉🥇"
    elif score >= 70:
        grade, emoji = "👍 Yaxshi (4)", "😊✨"
    elif score >= 50:
        grade, emoji = "📚 Qoniqarli (3)", "🙂📖"
    else:
        grade, emoji = "❌ Qoniqarsiz (2)", "😔📚"

    diff_label = DIFFICULTY_NAMES.get(difficulty, difficulty)
    encouragement = "🌟 Ajoyib natija!" if score >= 70 else "📚 Ko'proq mashq qiling!"

    result_text = (
        f"{emoji} <b>Test yakunlandi!</b>\n\n"
        f"━━━━━━━━━━━━━━\n"
        f"🎯 Daraja: <b>{diff_label}</b>\n"
        f"✅ To'g'ri: <b>{correct}/{total}</b>\n"
        f"❌ Noto'g'ri: <b>{wrong}/{total}</b>\n"
        f"📈 Ball: <b>{score}%</b>\n"
        f"🎓 Baho: <b>{grade}</b>\n"
        f"━━━━━━━━━━━━━━\n\n"
        f"{encouragement}"
    )

    save_test_result(callback.from_user.id, correct, wrong, started_at, difficulty)
    await state.clear()
    await callback.message.answer(result_text, reply_markup=main_menu_keyboard(is_paid=True), parse_mode="HTML")

@router.message(F.text == "📊 Mening natijalarim")
async def my_results(message: Message):
    results = get_user_results(message.from_user.id)
    if not results:
        await message.answer("📊 Hali test ishlamagansiz.\n📝 Testni boshlash tugmasini bosing!")
        return

    text = "📊 <b>Sizning natijalaringiz:</b>\n\n"
    for i, r in enumerate(results, 1):
        date = r['finished_at'][:10] if r['finished_at'] else "—"
        diff = DIFFICULTY_NAMES.get(r['difficulty'], r['difficulty'])
        text += f"{i}. 📅 {date}  {diff}\n   ✅ {r['correct_answers']}/30  📈 {r['score']}%\n\n"
    await message.answer(text, parse_mode="HTML")

@router.message(F.text == "🏆 Reyting")
async def leaderboard(message: Message):
    leaders = get_leaderboard(10)
    if not leaders:
        await message.answer("🏆 Hali reyting mavjud emas!")
        return

    medals = ["🥇", "🥈", "🥉"] + ["4️⃣","5️⃣","6️⃣","7️⃣","8️⃣","9️⃣","🔟"]
    text = "🏆 <b>Eng yaxshi natijalar:</b>\n\n"
    for i, row in enumerate(leaders):
        name = row['full_name'] or "Noma'lum"
        medal = medals[i] if i < len(medals) else f"{i+1}."
        text += f"{medal} <b>{name}</b> — {row['best_score']}%  ({row['attempts']} marta)\n"

    await message.answer(text, parse_mode="HTML")