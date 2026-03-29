"""
Biznes logika testlari — test_handler funksiyalari.
"""
import pytest
import json, base64, zlib, sys
sys.path.insert(0, '/tmp/fixed_bot')

from handlers.test_handler import (
    encode_questions, questions_to_miniapp, make_access_key
)


# ── encode/decode ──────────────────────────────────────────

def test_encode_questions_basic():
    qs = [{'id': 1, 't': 'Savol 1', 'a': 'A', 'b': 'B', 'c': 'C', 'd': 'D', 'ok': 'A',
           'img': '', 'type': 'choice', 'parts': 1, 'kw1': '', 'kw2': ''}]
    meta = {'subject': 'onatili', 'category': 'aralash', 'is_attestation': False}
    encoded = encode_questions(qs, meta)
    assert isinstance(encoded, str)
    assert len(encoded) > 10


def test_encode_decode_roundtrip():
    qs = [{'id': i, 't': f'Savol {i}', 'a': 'A', 'b': 'B', 'c': 'C', 'd': 'D',
           'ok': 'B', 'img': '', 'type': 'choice', 'parts': 1, 'kw1': '', 'kw2': ''}
          for i in range(1, 36)]
    meta = {'subject': 'onatili', 'category': 'aralash', 'is_attestation': False}
    encoded = encode_questions(qs, meta)

    # Decode
    b64    = encoded.replace('-', '+').replace('_', '/')
    raw    = zlib.decompress(base64.b64decode(b64))
    parsed = json.loads(raw.decode('utf-8'))
    assert len(parsed['questions']) == 35
    assert parsed['meta']['subject'] == 'onatili'


def test_encode_questions_empty():
    encoded = encode_questions([], {'subject': 'test'})
    assert isinstance(encoded, str)


def test_questions_to_miniapp():
    from unittest.mock import MagicMock
    q = MagicMock()
    q.id = 1
    q.question_text = 'Test savol'
    q.option_a = 'A varianti'
    q.option_b = 'B varianti'
    q.option_c = 'C varianti'
    q.option_d = 'D varianti'
    q.correct_answer = 'A'
    q.image_file_id = None
    q.question_type = 'choice'
    q.written_parts = 1
    q.keywords_1 = None
    q.keywords_2 = None

    result = questions_to_miniapp([q])
    assert len(result) == 1
    assert result[0]['t'] == 'Test savol'
    assert result[0]['ok'] == 'A'
    assert result[0]['img'] == ''


def test_questions_to_miniapp_written():
    from unittest.mock import MagicMock
    q = MagicMock()
    q.id = 2
    q.question_text = 'Yozma savol'
    q.option_a = q.option_b = q.option_c = q.option_d = None
    q.correct_answer = None
    q.image_file_id = None
    q.question_type = 'written'
    q.written_parts = 2
    q.keywords_1 = 'kalit1,kalit2'
    q.keywords_2 = 'kalit3'

    result = questions_to_miniapp([q])
    assert result[0]['type'] == 'written'
    assert result[0]['parts'] == 2
    assert result[0]['kw1'] == 'kalit1,kalit2'


def test_make_access_key():
    key = make_access_key('onatili', 'mavzu', 'fonetika')
    assert key == 'onatili:mavzu:fonetika'
    key2 = make_access_key('onatili', 'aralash')
    assert key2 == 'onatili:aralash:None'


# ── Attestatsiya baho tizimi ───────────────────────────────

def _grade(pct):
    """Attestatsiya baho tizimi."""
    if pct <= 59: return "Mutaxassis"
    elif pct <= 68: return "2-toifa"
    elif pct <= 78: return "1-toifa"
    elif pct <= 85: return "Oliy toifa"
    else: return "70% ustama"

@pytest.mark.parametrize("pct,expected", [
    (0,   "Mutaxassis"),
    (59,  "Mutaxassis"),
    (60,  "2-toifa"),
    (68,  "2-toifa"),
    (70,  "1-toifa"),
    (78,  "1-toifa"),
    (80,  "Oliy toifa"),
    (85,  "Oliy toifa"),
    (86,  "70% ustama"),
    (100, "70% ustama"),
])
def test_attestation_grade(pct, expected):
    assert _grade(pct) == expected


# ── Oddiy test baho tizimi ────────────────────────────────

def _regular_grade(pct):
    """Oddiy testlar ham attestatsiya tizimida baholanadi."""
    if pct >= 86: return "70% ustama"
    elif pct >= 80: return "Oliy toifa"
    elif pct >= 70: return "1-toifa"
    elif pct >= 60: return "2-toifa"
    else: return "Mutaxassis"

@pytest.mark.parametrize("pct,expected", [
    (100, "70% ustama"),
    (86,  "70% ustama"),
    (85,  "Oliy toifa"),
    (80,  "Oliy toifa"),
    (79,  "1-toifa"),
    (70,  "1-toifa"),
    (69,  "2-toifa"),
    (60,  "2-toifa"),
    (59,  "Mutaxassis"),
    (0,   "Mutaxassis"),
])
def test_regular_grade(pct, expected):
    assert _regular_grade(pct) == expected


# ── Config narxlar ────────────────────────────────────────

def test_config_prices():
    from config import config
    assert config.PRICE_DAILY == 10_000,     f"Kunlik narx: {config.PRICE_DAILY}"
    assert config.PRICE_MONTHLY == 100_000,  f"Oylik narx: {config.PRICE_MONTHLY}"
    assert config.PRICE_ATTESTATION == 5_000, f"Attestatsiya narx: {config.PRICE_ATTESTATION}"


def test_config_grades():
    from config import config
    # Ona tili bolimlar: kalit harf ('fonetika', 'imlo'...)
    if hasattr(config, 'ONA_TILI_BOLIMLAR'):
        assert len(config.ONA_TILI_BOLIMLAR) > 0
    if hasattr(config, 'JAHON_GRADES'):
        assert '6' in config.JAHON_GRADES


def test_config_no_difficulties():
    from config import config
    assert not hasattr(config, 'DIFFICULTIES') or config.DIFFICULTIES == {}, \
        "DIFFICULTIES olib tashlangan bo'lishi kerak"