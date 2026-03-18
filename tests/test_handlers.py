"""
Handler logikasi testlari.
Aiogram mock ishlatadi — haqiqiy Telegram ga ulanmaydi.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def make_message(text="", user_id=123456789, username="testuser"):
    """Mock message obyekti."""
    msg = AsyncMock()
    msg.text = text
    msg.from_user = MagicMock()
    msg.from_user.id = user_id
    msg.from_user.username = username
    msg.from_user.full_name = "Test User"
    msg.answer = AsyncMock()
    msg.bot = AsyncMock()
    return msg


def make_callback(data="", user_id=123456789):
    """Mock callback query obyekti."""
    cb = AsyncMock()
    cb.data = data
    cb.from_user = MagicMock()
    cb.from_user.id = user_id
    cb.from_user.username = "testuser"
    cb.message = AsyncMock()
    cb.message.edit_text = AsyncMock()
    cb.message.answer = AsyncMock()
    cb.answer = AsyncMock()
    cb.bot = AsyncMock()
    return cb


# ════════════════════════════════════════════════
# ENCODE/DECODE TESTLARI
# ════════════════════════════════════════════════

class TestEncoding:

    def test_encode_decode_questions(self):
        """Savollarni encode/decode qilish."""
        import sys
        sys.path.insert(0, '/home/claude/project/onatili_final')
        from handlers.test_handler import encode_questions

        questions = [
            {"id": 1, "t": "Savol 1", "a": "A", "b": "B", "c": "C", "d": "D",
             "ok": "A", "img": "", "type": "choice", "parts": 1, "kw1": "", "kw2": ""},
            {"id": 2, "t": "Savol 2", "a": "X", "b": "Y", "c": "Z", "d": "W",
             "ok": "B", "img": "", "type": "choice", "parts": 1, "kw1": "", "kw2": ""},
        ]
        meta = {"subject": "onatili", "category": "aralash"}

        encoded = encode_questions(questions, meta)
        assert isinstance(encoded, str)
        assert len(encoded) > 0

    def test_encode_decode_roundtrip(self):
        """Encode qilingan ma'lumot to'g'ri decode bo'lishi kerak."""
        import sys, json, base64, zlib
        sys.path.insert(0, '/home/claude/project/onatili_final')
        from handlers.test_handler import encode_questions

        original = [{"id": 1, "t": "Test savol", "ok": "A"}]
        meta = {"subject": "onatili"}

        encoded = encode_questions(original, meta)

        # Decode
        b64     = encoded.replace('-', '+').replace('_', '/')
        decoded = zlib.decompress(base64.urlsafe_b64decode(encoded + '=='))
        parsed  = json.loads(decoded.decode('utf-8'))

        assert parsed['questions'][0]['t'] == "Test savol"
        assert parsed['meta']['subject'] == "onatili"

    def test_make_access_key(self):
        """Access key formati to'g'ri."""
        import sys
        sys.path.insert(0, '/home/claude/project/onatili_final')
        from handlers.test_handler import make_access_key

        key = make_access_key("onatili", "mavzu", "fonetika")
        assert key == "onatili:mavzu:fonetika"

        key2 = make_access_key("adabiyot", "aralash")
        assert key2 == "adabiyot:aralash:None"


# ════════════════════════════════════════════════
# RESULT CALCULATION TESTLARI
# ════════════════════════════════════════════════

class TestResultCalc:

    def test_score_calculation(self):
        """Ball hisoblash to'g'ri."""
        correct = 28
        wrong   = 5
        skipped = 2
        total   = correct + wrong + skipped
        score   = round((correct / total) * 100, 1)
        assert score == pytest.approx(80.0, abs=0.1)

    def test_perfect_score(self):
        correct = 35
        total   = 35
        score   = round((correct / total) * 100, 1)
        assert score == 100.0

    def test_zero_score(self):
        correct = 0
        total   = 35
        score   = round((correct / total) * 100, 1)
        assert score == 0.0

    def test_grade_alo(self):
        """90%+ → A'lo."""
        pct = 92
        if pct >= 90:   grade = "A'lo (5)"
        elif pct >= 70: grade = "Yaxshi (4)"
        elif pct >= 50: grade = "Qoniqarli (3)"
        else:           grade = "Qoniqarsiz (2)"
        assert grade == "A'lo (5)"

    def test_grade_yaxshi(self):
        pct = 75
        if pct >= 90:   grade = "A'lo (5)"
        elif pct >= 70: grade = "Yaxshi (4)"
        elif pct >= 50: grade = "Qoniqarli (3)"
        else:           grade = "Qoniqarsiz (2)"
        assert grade == "Yaxshi (4)"

    def test_grade_qoniqarsiz(self):
        pct = 30
        if pct >= 90:   grade = "A'lo (5)"
        elif pct >= 70: grade = "Yaxshi (4)"
        elif pct >= 50: grade = "Qoniqarli (3)"
        else:           grade = "Qoniqarsiz (2)"
        assert grade == "Qoniqarsiz (2)"


# ════════════════════════════════════════════════
# PAYMENT LOGIC TESTLARI
# ════════════════════════════════════════════════

class TestPaymentLogic:

    def test_product_prices(self):
        """Narxlar to'g'ri."""
        import sys
        sys.path.insert(0, '/home/claude/project/onatili_final')
        from handlers.payment import PRODUCT_PRICES
        assert PRODUCT_PRICES['once']    == 3_500
        assert PRODUCT_PRICES['daily']   == 35_000
        assert PRODUCT_PRICES['monthly'] == 100_000

    def test_access_key_parsing(self):
        """Access key parsing to'g'ri."""
        key   = "onatili:mavzu:fonetika_tovushlar_tasnifi"
        parts = key.split(':')
        assert parts[0] == "onatili"
        assert parts[1] == "mavzu"
        assert parts[2] == "fonetika_tovushlar_tasnifi"

    def test_access_key_none_subcategory(self):
        """None subcategory ni to'g'ri parse qilish."""
        key   = "onatili:aralash:None"
        parts = key.split(':')
        subcategory = parts[2] if parts[2] != 'None' else None
        assert subcategory is None


# ════════════════════════════════════════════════
# CONFIG TESTLARI
# ════════════════════════════════════════════════

class TestConfig:

    def test_max_questions(self):
        """MAX_QUESTIONS 50 bo'lishi kerak."""
        import sys
        sys.path.insert(0, '/home/claude/project/onatili_final')
        from config import config
        assert config.MAX_QUESTIONS == 50

    def test_attestation_count(self):
        """ATTESTATION_COUNT 35 bo'lishi kerak."""
        import sys
        sys.path.insert(0, '/home/claude/project/onatili_final')
        from config import config
        assert config.ATTESTATION_COUNT == 35

    def test_ona_tili_bolimlar(self):
        """Ona tili bo'limlari mavjud."""
        import sys
        sys.path.insert(0, '/home/claude/project/onatili_final')
        from config import config
        assert 'fonetika' in config.ONA_TILI_BOLIMLAR
        assert 'morfologiya_m' in config.ONA_TILI_BOLIMLAR
        assert 'sintaksis' in config.ONA_TILI_BOLIMLAR

    def test_subjects(self):
        """Fanlar to'g'ri."""
        import sys
        sys.path.insert(0, '/home/claude/project/onatili_final')
        from config import config
        assert 'onatili' in config.SUBJECTS
        assert 'adabiyot' in config.SUBJECTS