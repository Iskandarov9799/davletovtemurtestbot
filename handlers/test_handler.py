from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from datetime import datetime

from database.db import (
    get_random_questions, save_test_result, get_user_results,
    is_user_paid, is_user_registered
)
from keyboards.keyboards import test_answer_keyboard, main_menu_keyboard, start_test_keyboard
from states import TestStates

router = Router()

TOTAL_QUESTIONS = 30

def format_question(q, index: int, total: int) -> str:
    """Savol matnini formatlash"""
    progress_bar = "▓" * (index + 1) + "░" * (total - index - 1)

    return (
        f"📊 <b>{index + 1}/{total}</b> [{progress_bar}]\n\n"
        f"❓ <b>{q['question_text']}</b>\n\n"
        f"🅰 {q['option_a']}\n"
        f"🅱 {q['option_b']}\n"
        f"🅲 {q['option_c']}\n"
        f"🅳 {q['option_d']}"
    )

@router.message(F.text == "📝 Testni boshlash")
async def start_test_prompt(message: Message, state: FSMContext):
    """Test boshlashdan oldin tasdiqlash"""

    if not is_user_registered(message.from_user.id):
        await message.answer("❌ Avval ro'yxatdan o'ting! /start")
        return

    if not is_user_paid(message.from_user.id):
        await message.answer(
            "❌ Test ishlatish uchun avval to'lov qilishingiz kerak!\n"
            "💳 \"To'lov qilish\" tugmasini bosing.",
            reply_markup=main_menu_keyboard(is_paid=False)
        )
        return

    await message.answer(
        "📝 <b>Ona tili va Adabiyot Testi</b>\n\n"
        "📋 Qoidalar:\n"
        "• Jami <b>30 ta savol</b>\n"
        "• Har bir savolda 4 ta variant\n"
        "• Faqat 1 ta to'g'ri javob\n"
        "• Vaqt cheklanmagan\n\n"
        "🎯 Testni boshlashga tayyormisiz?",
        reply_markup=start_test_keyboard(),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "start_test")
async def begin_test(callback: CallbackQuery, state: FSMContext):
    """Testni boshlash"""

    if not is_user_paid(callback.from_user.id):
        await callback.answer("❌ To'lov qilinmagan!", show_alert=True)
        return

    questions = get_random_questions(subject="ona_tili", count=TOTAL_QUESTIONS)

    if len(questions) < TOTAL_QUESTIONS:
    # If not enough questions, use what we have
        if len(questions) == 0:
            await callback.answer("❌ Savollar topilmadi!", show_alert=True)
            return

    # Convert to list of dicts
    q_list = [dict(q) for q in questions]

    await state.set_data({
        "questions": q_list,
        "current_index": 0,
        "answers": {},
        "correct": 0,
        "wrong": 0,
        "started_at": datetime.now().isoformat()
    })

    await state.set_state(TestStates.answering)

    await callback.message.delete()

    # Send first question
    first_q = q_list[0]
    await callback.message.answer(
        format_question(first_q, 0, len(q_list)),
        reply_markup=test_answer_keyboard(0),
        parse_mode="HTML"
    )

    await callback.answer()

@router.callback_query(TestStates.answering, F.data.startswith("answer:"))
async def process_answer(callback: CallbackQuery, state: FSMContext):
    """Javobni qayta ishlash"""

    parts = callback.data.split(":")
    q_index = int(parts[1])
    selected = parts[2]  # A, B, C, or D

    data = await state.get_data()
    questions = data["questions"]
    current_index = data["current_index"]

    # Prevent answering old questions
    if q_index != current_index:
        await callback.answer("⚠️ Bu savol allaqachon o'tib ketgan!", show_alert=True)
        return

    current_q = questions[current_index]
    correct_answer = current_q["correct_answer"]
    is_correct = selected == correct_answer

    # Update stats
    correct = data["correct"] + (1 if is_correct else 0)
    wrong = data["wrong"] + (0 if is_correct else 1)
    answers = data["answers"]
    answers[str(current_index)] = selected

    # Show result for this question
    if is_correct:
        result_text = "✅ <b>To'g'ri!</b>"
    else:
        option_map = {"A": current_q["option_a"], "B": current_q["option_b"],
                      "C": current_q["option_c"], "D": current_q["option_d"]}
        result_text = (
            f"❌ <b>Noto'g'ri!</b>\n"
            f"To'g'ri javob: <b>{correct_answer}) {option_map[correct_answer]}</b>"
        )

    # Check if last question
    next_index = current_index + 1
    total = len(questions)

    if next_index >= total:
        # Test finished!
        await state.update_data(correct=correct, wrong=wrong, answers=answers)
        await finish_test(callback, state, correct, wrong, data["started_at"])
        await callback.answer()
        return

    # Update state
    await state.update_data(
        current_index=next_index,
        correct=correct,
        wrong=wrong,
        answers=answers
    )

    # Edit current message to show result
    await callback.message.edit_text(
        format_question(current_q, current_index, total) + f"\n\n{result_text}",
        parse_mode="HTML"
    )

    # Send next question
    next_q = questions[next_index]
    await callback.message.answer(
        format_question(next_q, next_index, total),
        reply_markup=test_answer_keyboard(next_index),
        parse_mode="HTML"
    )

    await callback.answer()

async def finish_test(callback: CallbackQuery, state: FSMContext, correct: int, wrong: int, started_at: str):
    """Test yakunlanishi"""

    total = TOTAL_QUESTIONS
    score = round((correct / total) * 100, 1)

    # Save to DB
    save_test_result(
        telegram_id=callback.from_user.id,
        correct=correct,
        wrong=wrong,
        started_at=started_at
    )

    # Determine grade
    if score >= 90:
        grade = "🏆 A'lo (5)"
        emoji = "🎉🥇"
    elif score >= 70:
        grade = "👍 Yaxshi (4)"
        emoji = "😊✨"
    elif score >= 50:
        grade = "📚 Qoniqarli (3)"
        emoji = "🙂📖"
    else:
        grade = "❌ Qoniqarsiz (2)"
        emoji = "😔📚"

    result_text = (
        f"{emoji} <b>Test yakunlandi!</b>\n\n"
        f"━━━━━━━━━━━━━━\n"
        f"📊 <b>Natijangiz:</b>\n\n"
        f"✅ To'g'ri: <b>{correct}/{total}</b>\n"
        f"❌ Noto'g'ri: <b>{wrong}/{total}</b>\n"
        f"📈 Ball: <b>{score}%</b>\n"
        f"🎓 Baho: <b>{grade}</b>\n"
        f"━━━━━━━━━━━━━━\n\n"
        f"{'🌟 Ajoyib natija! Davom eting!' if score >= 70 else '📚 Koʻproq oʻqishni davom eting!'}"
    )

    await state.clear()

    await callback.message.answer(
        result_text,
        reply_markup=main_menu_keyboard(is_paid=True),
        parse_mode="HTML"
    )

@router.message(F.text == "📊 Mening natijalarim")
async def my_results(message: Message):
    """Foydalanuvchining natijalari"""

    results = get_user_results(message.from_user.id)

    if not results:
        await message.answer(
            "📊 Siz hali test ishlamagansiz.\n"
            "📝 \"Testni boshlash\" tugmasini bosing!"
        )
        return

    text = "📊 <b>Sizning natijalaringiz:</b>\n\n"

    for i, r in enumerate(results, 1):
        date = r['finished_at'][:10] if r['finished_at'] else "Noma'lum"
        text += (
            f"{i}. 📅 {date}\n"
            f"   ✅ {r['correct_answers']}/30 | 📈 {r['score']}%\n\n"
        )

    await message.answer(text, parse_mode="HTML")