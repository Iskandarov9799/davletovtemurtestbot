"""
pytest uchun fixtures — SQLite in-memory DB ishlatadi.
Haqiqiy PostgreSQL ga tegmaydi.
"""
import sys, os, asyncio
sys.path.insert(0, '/home/bot')
os.environ.setdefault('BOT_TOKEN',    'test:token')
os.environ.setdefault('DATABASE_URL', 'sqlite+aiosqlite:///:memory:')
os.environ.setdefault('ADMIN_IDS',    '[999]')
os.environ.setdefault('MINI_APP_URL', 'https://test.example.com')
os.environ.setdefault('IMAGES_DIR',   '/tmp/test_images')
os.environ.setdefault('IMAGES_URL',   'http://localhost/images')

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from database.models import Base
import database.connection as _conn


@pytest.fixture(scope='session')
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope='session', autouse=True)
async def setup_db():
    """SQLite in-memory DB yaratish."""
    engine = create_async_engine('sqlite+aiosqlite:///:memory:', echo=False)
    _conn._engine = engine
    _conn.AsyncSessionLocal = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()