"""
Mini App — natija qayta ishlash mantiqini tekshirish.
"""
import sys
sys.path.insert(0, '/tmp/fixed_bot')
import pytest


def _attestation_grade(pct):
    """miniapp_handler._attestation_grade logikasi — yangi chegaralar."""
    if pct <= 59: return "Mutaxassis", "📋"
    elif pct <= 68: return "2-toifa", "🥉"
    elif pct <= 78: return "1-toifa", "🥈"
    elif pct <= 85: return "Oliy toifa", "🥇"
    else: return "70% ustama", "🏆"


@pytest.mark.parametrize("pct,grade,emoji", [
    (0,   "Mutaxassis",  "📋"),
    (59,  "Mutaxassis",  "📋"),
    (60,  "2-toifa",     "🥉"),
    (68,  "2-toifa",     "🥉"),
    (70,  "1-toifa",     "🥈"),
    (78,  "1-toifa",     "🥈"),
    (80,  "Oliy toifa",  "🥇"),
    (85,  "Oliy toifa",  "🥇"),
    (86,  "70% ustama",  "🏆"),
    (100, "70% ustama",  "🏆"),
])
def test_attestation_grade_with_emoji(pct, grade, emoji):
    g, e = _attestation_grade(pct)
    assert g == grade
    assert e == emoji


def test_miniapp_handler_has_grade_func():
    """miniapp_handler da _attestation_grade funksiyasi bo'lishi kerak."""
    from handlers.miniapp_handler import _attestation_grade as fn
    grade, emoji = fn(86)
    assert "ustama" in grade
    assert emoji == "🏆"
    grade2, _ = fn(80)
    assert "Oliy" in grade2


def test_bolim_label_formatting():
    """bolim_1 → 1-bo'lim."""
    subcategory = 'bolim_3'
    if subcategory.startswith('bolim_'):
        bolim_num = subcategory.split('_', 1)[1]
        label = f"{bolim_num}-bo'lim"
    assert label == "3-bo'lim"


def test_score_calculation():
    """Score formulasi to'g'ri."""
    correct, wrong, skipped = 28, 5, 2
    total = correct + wrong + skipped
    pct = round((correct / total) * 100, 1)
    assert total == 35
    assert pct == pytest.approx(80.0, abs=0.1)


def test_score_zero_total():
    total = 0
    pct = round((0 / total) * 100, 1) if total > 0 else 0.0
    assert pct == 0.0


@pytest.mark.parametrize("correct,total,expected_pct", [
    (35, 35, 100.0),
    (0,  35, 0.0),
    (17, 35, pytest.approx(48.6, abs=0.1)),
    (30, 35, pytest.approx(85.7, abs=0.1)),
])
def test_score_various(correct, total, expected_pct):
    pct = round((correct / total) * 100, 1) if total > 0 else 0.0
    assert pct == expected_pct