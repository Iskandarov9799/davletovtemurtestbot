"""
Test konfiguratsiyasi — SQLite in-memory DB ishlatadi.
Haqiqiy PostgreSQL ga tegmaydi.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from database.models import Base
import database.connection as _conn


# ── Event loop ────────────────────────────────
@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ── Test DB (SQLite in-memory) ────────────────
@pytest_asyncio.fixture(scope="function")
async def test_db():
    """Har test uchun yangi bo'sh DB."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # db.py global o'zgaruvchilarini test DB ga yo'naltirish
    _conn._engine = engine
    _conn.AsyncSessionLocal = session_factory

    yield session_factory

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()
    _conn._engine = None
    _conn.AsyncSessionLocal = None


# ── Yordamchi fixture-lar ─────────────────────
@pytest_asyncio.fixture
async def sample_user(test_db):
    """Test foydalanuvchi yaratish."""
    from database.db import create_user
    await create_user(telegram_id=123456789, full_name="Test User", username="testuser")
    return 123456789


@pytest_asyncio.fixture
async def sample_question(test_db):
    """Test savol yaratish."""
    from database.db import add_question
    await add_question(
        subject="onatili",
        category="mavzu",
        question_text="O'zbek tilida nechta unli tovush bor?",
        option_a="5 ta",
        option_b="6 ta",
        option_c="7 ta",
        option_d="8 ta",
        correct_answer="B",
        subcategory="fonetika_tovushlar_tasnifi",
        question_type="choice",
        written_parts=1,
    )
    from database.db import get_questions
    questions = await get_questions("onatili", "mavzu", subcategory="fonetika_tovushlar_tasnifi")
    return questions[0] if questions else None