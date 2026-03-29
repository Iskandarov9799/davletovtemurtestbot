"""
DB — test natijalari va statistika testlari.
"""
import pytest
from database.db import (
    create_user, save_test_result, get_user_results,
    get_leaderboard, get_full_stats, add_question,
)

TID  = 400001
TID2 = 400002


@pytest.mark.asyncio
async def test_save_and_get_results():
    await create_user(TID, "Result User")
    score = await save_test_result(
        telegram_id=TID, subject='onatili', category='aralash',
        subcategory=None, difficulty=None,
        correct=28, wrong=5, skipped=2
    )
    assert score == pytest.approx(80.0, abs=1)
    results = await get_user_results(TID)
    assert len(results) >= 1
    assert results[0].correct == 28


@pytest.mark.asyncio
async def test_result_attempt_number():
    """Urinish raqami to'g'ri hisoblanishi kerak."""
    await save_test_result(
        telegram_id=TID, subject='onatili', category='aralash',
        subcategory=None, difficulty=None,
        correct=30, wrong=3, skipped=2
    )
    results = await get_user_results(TID, limit=10)
    attempts = sorted([r.attempt_number for r in results
                       if r.subject == 'onatili' and r.category == 'aralash'])
    assert attempts == list(range(1, len(attempts) + 1))


@pytest.mark.asyncio
async def test_result_score_formula():
    """Score = correct / total * 100."""
    score = await save_test_result(
        telegram_id=TID, subject='adabiyot', category='sinf',
        subcategory='7', difficulty=None,
        correct=35, wrong=0, skipped=0
    )
    assert score == 100.0


@pytest.mark.asyncio
async def test_result_empty_test():
    """total=0 bo'lsa 0.0 qaytarsin."""
    score = await save_test_result(
        telegram_id=TID, subject='adabiyot', category='sinf',
        subcategory='8', difficulty=None,
        correct=0, wrong=0, skipped=0
    )
    assert score == 0.0


@pytest.mark.asyncio
async def test_attestation_result():
    score = await save_test_result(
        telegram_id=TID, subject='attestation', category='attestation',
        subcategory='bolim_1', difficulty=None,
        correct=30, wrong=5, skipped=0, is_attestation=True
    )
    results = await get_user_results(TID)
    att_results = [r for r in results if r.is_attestation]
    assert len(att_results) >= 1


@pytest.mark.asyncio
async def test_get_user_results_limit():
    await create_user(TID2, "Limit User")
    for i in range(15):
        await save_test_result(
            telegram_id=TID2, subject='onatili', category='aralash',
            subcategory=None, difficulty=None,
            correct=i, wrong=35-i, skipped=0
        )
    results = await get_user_results(TID2, limit=10)
    assert len(results) == 10


@pytest.mark.asyncio
async def test_leaderboard():
    leaders = await get_leaderboard(5)
    assert isinstance(leaders, list)
    if len(leaders) >= 2:
        assert leaders[0].best_score >= leaders[1].best_score


@pytest.mark.asyncio
async def test_full_stats():
    await add_question(
        subject='onatili', category='mavzu', subcategory='sintaksis',
        question_text='Statistika test savoli',
        option_a='A', option_b='B', option_c='C', option_d='D',
        correct_answer='A'
    )
    stats = await get_full_stats()
    assert stats['total_users'] >= 1
    assert stats['total_questions'] >= 1
    assert stats['total_tests'] >= 1
    assert stats['onatili_q'] >= 1
    assert 'avg_score' in stats
    assert isinstance(stats['avg_score'], float)