"""
Database funksiyalari testlari.
Barcha CRUD operatsiyalarini tekshiradi.
"""
import pytest
import pytest_asyncio
from database.db import (
    create_user, get_user, update_user_phone, is_registered,
    add_question, get_questions, count_questions, delete_question,
    get_access_status, mark_free_used, mark_once_used,
    create_purchase, confirm_purchase, reject_purchase,
    grant_attestation, has_attestation,
    save_test_result, get_user_results,
)


# ════════════════════════════════════════════════
# USER TESTLARI
# ════════════════════════════════════════════════

class TestUser:

    @pytest.mark.asyncio
    async def test_create_user(self, test_db):
        """Foydalanuvchi yaratish."""
        await create_user(111, "Ali Valiyev", "ali_v")
        user = await get_user(111)
        assert user is not None
        assert user.full_name == "Ali Valiyev"
        assert user.username == "ali_v"
        assert user.is_registered is False

    @pytest.mark.asyncio
    async def test_create_duplicate_user(self, test_db):
        """Bir xil telegram_id bilan ikki marta yaratish xato bermasligi kerak."""
        await create_user(222, "User 1")
        await create_user(222, "User 2")  # ikkinchi marta — o'tkazib yuboradi
        user = await get_user(222)
        assert user.full_name == "User 1"  # birinchisi saqlanadi

    @pytest.mark.asyncio
    async def test_update_phone(self, test_db):
        """Telefon raqam yangilash."""
        await create_user(333, "Botir")
        await update_user_phone(333, "+998901234567")
        user = await get_user(333)
        assert user.phone_number == "+998901234567"
        assert user.is_registered is True

    @pytest.mark.asyncio
    async def test_is_registered(self, test_db):
        """Ro'yxatdan o'tganlik tekshiruvi."""
        await create_user(444, "Sardor")
        assert await is_registered(444) is False
        await update_user_phone(444, "+998901111111")
        assert await is_registered(444) is True

    @pytest.mark.asyncio
    async def test_get_nonexistent_user(self, test_db):
        """Mavjud bo'lmagan foydalanuvchi."""
        user = await get_user(999999)
        assert user is None


# ════════════════════════════════════════════════
# QUESTION TESTLARI
# ════════════════════════════════════════════════

class TestQuestion:

    @pytest.mark.asyncio
    async def test_add_choice_question(self, test_db):
        """Variantli savol qo'shish."""
        await add_question(
            subject="onatili", category="mavzu",
            question_text="Fonetika nimani o'rganadi?",
            option_a="So'z ma'nosini", option_b="Tovush va harflarni",
            option_c="Gap tuzilishini", option_d="So'z yasalishini",
            correct_answer="B",
            subcategory="fonetika",
            question_type="choice",
        )
        cnt = await count_questions(subject="onatili", category="mavzu")
        assert cnt == 1

    @pytest.mark.asyncio
    async def test_add_written_question(self, test_db):
        """Yozma savol qo'shish."""
        await add_question(
            subject="milliy", category="milliy",
            question_text="Fonetikani izohlang.",
            option_a=None, option_b=None,
            option_c=None, option_d=None,
            correct_answer=None,
            is_attestation=True,
            order_num=36,
            question_type="written",
            written_parts=1,
            keywords_1="tovush, harf, talaffuz",
        )
        cnt = await count_questions(subject="milliy", category="milliy", is_attestation=True)
        assert cnt == 1

    @pytest.mark.asyncio
    async def test_get_questions_random(self, test_db):
        """Savollarni olish."""
        for i in range(5):
            await add_question(
                subject="onatili", category="aralash",
                question_text=f"Savol {i}",
                option_a="A", option_b="B", option_c="C", option_d="D",
                correct_answer="A", question_type="choice",
            )
        questions = await get_questions("onatili", "aralash", count=3)
        assert len(questions) == 3

    @pytest.mark.asyncio
    async def test_get_questions_attestation_order(self, test_db):
        """Attestatsiya savollari tartib bo'yicha kelishi kerak."""
        for order in [3, 1, 2]:
            await add_question(
                subject="attestation", category="attestation",
                question_text=f"Savol {order}",
                option_a="A", option_b="B", option_c="C", option_d="D",
                correct_answer="A", is_attestation=True,
                order_num=order, question_type="choice",
            )
        questions = await get_questions("attestation", "attestation", is_attestation=True)
        orders = [q.order_num for q in questions]
        assert orders == sorted(orders)

    @pytest.mark.asyncio
    async def test_count_questions_filters(self, test_db):
        """Filtrlar bilan savollarni hisoblash."""
        await add_question(
            subject="onatili", category="mavzu",
            question_text="Savol 1",
            option_a="A", option_b="B", option_c="C", option_d="D",
            correct_answer="A", subcategory="fonetika",
        )
        await add_question(
            subject="adabiyot", category="aralash",
            question_text="Savol 2",
            option_a="A", option_b="B", option_c="C", option_d="D",
            correct_answer="B",
        )
        assert await count_questions(subject="onatili") == 1
        assert await count_questions(subject="adabiyot") == 1
        assert await count_questions() == 2

    @pytest.mark.asyncio
    async def test_delete_question(self, test_db, sample_question):
        """Savol o'chirish."""
        qid = sample_question.id
        await delete_question(qid)
        cnt = await count_questions(subject="onatili")
        assert cnt == 0

    @pytest.mark.asyncio
    async def test_written_question_null_options(self, test_db):
        """Yozma savol option_a=None bo'lishi mumkin."""
        await add_question(
            subject="milliy", category="milliy",
            question_text="Yozma savol",
            option_a=None, option_b=None,
            option_c=None, option_d=None,
            correct_answer=None,
            is_attestation=True, order_num=36,
            question_type="written", written_parts=1,
            keywords_1="kalit",
        )
        questions = await get_questions("milliy", "milliy", is_attestation=True)
        assert len(questions) == 1
        assert questions[0].option_a is None
        assert questions[0].question_type == "written"


# ════════════════════════════════════════════════
# ACCESS TESTLARI
# ════════════════════════════════════════════════

class TestAccess:

    @pytest.mark.asyncio
    async def test_first_access_is_free(self, test_db, sample_user):
        """Birinchi kirish bepul bo'lishi kerak."""
        status = await get_access_status(sample_user, "onatili:mavzu:fonetika")
        assert status == "free"

    @pytest.mark.asyncio
    async def test_after_free_used_is_buy(self, test_db, sample_user):
        """Bepul ishlatilgandan keyin — to'lov kerak."""
        key = "onatili:mavzu:fonetika"
        await mark_free_used(sample_user, key)
        status = await get_access_status(sample_user, key)
        assert status == "buy"

    @pytest.mark.asyncio
    async def test_once_payment_gives_access(self, test_db, sample_user):
        """Once to'lov tasdiqlangandan keyin — paid."""
        key = "onatili:mavzu:fonetika"
        await mark_free_used(sample_user, key)

        purchase_id = await create_purchase(
            telegram_id=sample_user,
            product_type="once",
            amount=3500,
            check_photo="file_id_123",
            retry_key=key
        )
        await confirm_purchase(purchase_id, admin_id=999)

        status = await get_access_status(sample_user, key)
        assert status == "paid"

    @pytest.mark.asyncio
    async def test_once_payment_used_becomes_buy(self, test_db, sample_user):
        """Once to'lov ishlatilgandan keyin — buy."""
        key = "onatili:aralash:None"
        await mark_free_used(sample_user, key)

        purchase_id = await create_purchase(
            telegram_id=sample_user,
            product_type="once",
            amount=3500,
            check_photo="file_id_456",
            retry_key=key
        )
        await confirm_purchase(purchase_id, admin_id=999)
        await mark_once_used(sample_user, key)

        status = await get_access_status(sample_user, key)
        assert status == "buy"

    @pytest.mark.asyncio
    async def test_different_keys_independent(self, test_db, sample_user):
        """Har xil kalit — mustaqil holat."""
        key1 = "onatili:mavzu:fonetika"
        key2 = "adabiyot:aralash:None"
        await mark_free_used(sample_user, key1)
        assert await get_access_status(sample_user, key2) == "free"


# ════════════════════════════════════════════════
# PURCHASE TESTLARI
# ════════════════════════════════════════════════

class TestPurchase:

    @pytest.mark.asyncio
    async def test_create_purchase(self, test_db, sample_user):
        """To'lov yaratish."""
        pid = await create_purchase(
            telegram_id=sample_user,
            product_type="daily",
            amount=35000,
            check_photo="photo_id",
        )
        assert isinstance(pid, int)
        assert pid > 0

    @pytest.mark.asyncio
    async def test_confirm_purchase(self, test_db, sample_user):
        """To'lovni tasdiqlash."""
        pid = await create_purchase(
            telegram_id=sample_user,
            product_type="monthly",
            amount=100000,
            check_photo="photo_id",
        )
        await confirm_purchase(pid, admin_id=999)
        from database.db import get_purchase_by_id
        p = await get_purchase_by_id(pid)
        assert p.status == "confirmed"

    @pytest.mark.asyncio
    async def test_reject_purchase(self, test_db, sample_user):
        """To'lovni rad etish."""
        pid = await create_purchase(
            telegram_id=sample_user,
            product_type="once",
            amount=3500,
            check_photo="photo_id",
        )
        await reject_purchase(pid, admin_id=999)
        from database.db import get_purchase_by_id
        p = await get_purchase_by_id(pid)
        assert p.status == "rejected"


# ════════════════════════════════════════════════
# ATTESTATION TESTLARI
# ════════════════════════════════════════════════

class TestAttestation:

    @pytest.mark.asyncio
    async def test_grant_attestation(self, test_db, sample_user):
        """Attestatsiya huquqi berish."""
        assert await has_attestation(sample_user, "attestation") is False
        await grant_attestation(sample_user, "attestation", "miniapp")
        assert await has_attestation(sample_user, "attestation") is True

    @pytest.mark.asyncio
    async def test_grant_attestation_idempotent(self, test_db, sample_user):
        """Ikki marta grant berish xato bermasligi kerak."""
        await grant_attestation(sample_user, "attestation", "miniapp")
        await grant_attestation(sample_user, "attestation", "miniapp")
        assert await has_attestation(sample_user, "attestation") is True


# ════════════════════════════════════════════════
# TEST RESULT TESTLARI
# ════════════════════════════════════════════════

class TestResult:

    @pytest.mark.asyncio
    async def test_save_result(self, test_db, sample_user):
        """Test natijasini saqlash."""
        score = await save_test_result(
            telegram_id=sample_user,
            subject="onatili", category="mavzu",
            subcategory="fonetika", difficulty=None,
            correct=28, wrong=5, skipped=2,
        )
        assert score == pytest.approx(80.0, abs=1.0)

    @pytest.mark.asyncio
    async def test_perfect_score(self, test_db, sample_user):
        """100% natija."""
        score = await save_test_result(
            telegram_id=sample_user,
            subject="onatili", category="aralash",
            subcategory=None, difficulty=None,
            correct=35, wrong=0, skipped=0,
        )
        assert score == 100.0

    @pytest.mark.asyncio
    async def test_zero_score(self, test_db, sample_user):
        """0% natija."""
        score = await save_test_result(
            telegram_id=sample_user,
            subject="adabiyot", category="aralash",
            subcategory=None, difficulty=None,
            correct=0, wrong=35, skipped=0,
        )
        assert score == 0.0

    @pytest.mark.asyncio
    async def test_get_results(self, test_db, sample_user):
        """Natijalarni olish."""
        await save_test_result(
            telegram_id=sample_user, subject="onatili",
            category="aralash", subcategory=None, difficulty=None,
            correct=20, wrong=10, skipped=5,
        )
        results = await get_user_results(sample_user)
        assert len(results) == 1
        assert results[0].correct == 20

    @pytest.mark.asyncio
    async def test_multiple_attempts(self, test_db, sample_user):
        """Bir necha urinish."""
        for i in range(3):
            await save_test_result(
                telegram_id=sample_user, subject="onatili",
                category="mavzu", subcategory="fonetika", difficulty=None,
                correct=i * 10, wrong=35 - i * 10, skipped=0,
            )
        results = await get_user_results(sample_user, limit=10)
        assert len(results) == 3