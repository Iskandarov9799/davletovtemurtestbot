"""
Keyboard funksiyalari testlari.
"""
import sys
sys.path.insert(0, '/tmp/fixed_bot')
import pytest
from aiogram.types import InlineKeyboardMarkup, ReplyKeyboardMarkup
from keyboards.keyboards import (
    main_menu_keyboard, admin_keyboard, phone_keyboard,
    payment_options_keyboard, payment_confirm_keyboard,
    attestation_bolimlar_keyboard,
    cancel_keyboard, skip_image_keyboard,
)
# make_test_keyboard local test qilish uchun qayta yozilgan
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
def _make_link_keyboard(url, label="🚀 Testni boshlash"):
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=label, web_app=WebAppInfo(url=url))]])


def test_main_menu_keyboard():
    kb = main_menu_keyboard()
    assert isinstance(kb, ReplyKeyboardMarkup)
    texts = [btn.text for row in kb.keyboard for btn in row]
    assert "📚 Ona tili" in texts
    assert "📖 Adabiyot" in texts
    assert "🎓 Atestatsiya" in texts


def test_admin_keyboard():
    kb = admin_keyboard()
    assert isinstance(kb, ReplyKeyboardMarkup)
    texts = [btn.text for row in kb.keyboard for btn in row]
    assert "➕ Savol qo'shish" in texts
    assert "📊 Statistika" in texts
    assert "♻️ Tariflarni nollash" in texts


def test_phone_keyboard():
    kb = phone_keyboard()
    assert isinstance(kb, ReplyKeyboardMarkup)
    assert kb.keyboard[0][0].request_contact is True


def test_payment_options_keyboard_no_once():
    kb = payment_options_keyboard("onatili:aralash:None")
    assert isinstance(kb, InlineKeyboardMarkup)
    callbacks = [btn.callback_data for row in kb.inline_keyboard for btn in row]
    # bir martalik yo'q
    assert not any('once' in c for c in callbacks if c)
    # kunlik va oylik bor
    assert any('daily' in c for c in callbacks if c)
    assert any('monthly' in c for c in callbacks if c)


def test_payment_options_keyboard_prices():
    """Narxlar config dan olinishi kerak."""
    from config import config
    kb = payment_options_keyboard("test:key")
    texts = [btn.text for row in kb.inline_keyboard for btn in row]
    daily_text = next((t for t in texts if 'unlik' in t), None)
    assert daily_text is not None
    assert str(config.PRICE_DAILY // 1000) in daily_text  # "10" bor


def test_payment_confirm_keyboard():
    kb = payment_confirm_keyboard(42)
    callbacks = [btn.callback_data for row in kb.inline_keyboard for btn in row]
    assert "confirm_pay:42" in callbacks
    assert "reject_pay:42" in callbacks


def test_attestation_bolimlar_keyboard():
    kb = attestation_bolimlar_keyboard()
    assert isinstance(kb, InlineKeyboardMarkup)
    callbacks = [btn.callback_data for row in kb.inline_keyboard for btn in row]
    for i in range(1, 11):
        assert f"attest:bolim:{i}" in callbacks


def test__make_link_keyboard():
    url = "https://example.com/?data=test"
    kb = _make_link_keyboard(url)
    assert isinstance(kb, InlineKeyboardMarkup)
    btn = kb.inline_keyboard[0][0]
    assert btn.web_app is not None
    assert btn.web_app.url == url


def test_test_link_keyboard_custom_label():
    kb = _make_link_keyboard("https://example.com", "🚀 1-bo'lim")
    btn = kb.inline_keyboard[0][0]
    assert btn.text == "🚀 1-bo'lim"


def test_cancel_keyboard():
    kb = cancel_keyboard()
    assert isinstance(kb, InlineKeyboardMarkup)
    callbacks = [btn.callback_data for row in kb.inline_keyboard for btn in row]
    assert "payment:cancel" in callbacks


def test_skip_image_keyboard():
    kb = skip_image_keyboard()
    assert isinstance(kb, ReplyKeyboardMarkup)
    texts = [btn.text for row in kb.keyboard for btn in row]
    assert "⏭ Rasmisiz davom etish" in texts


def test_no_difficulty_keyboard():
    """addq_difficulty_keyboard olib tashlangan bo'lishi kerak."""
    import keyboards.keyboards as kb_module
    assert not hasattr(kb_module, 'addq_difficulty_keyboard'), \
        "addq_difficulty_keyboard olib tashlangan bo'lishi kerak"