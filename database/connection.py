import ssl
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from database.models import Base


def _clean_url(raw: str) -> str:
    if raw.startswith("postgres://"):
        raw = raw.replace("postgres://", "postgresql+asyncpg://", 1)
    elif raw.startswith("postgresql://"):
        raw = raw.replace("postgresql://", "postgresql+asyncpg://", 1)

    parsed = urlparse(raw)
    params = parse_qs(parsed.query, keep_blank_values=True)
    remove_keys = {'sslmode', 'ssl', 'channel_binding', 'connect_timeout', 'application_name'}
    cleaned = {k: v for k, v in params.items() if k not in remove_keys}
    new_query = urlencode(cleaned, doseq=True)
    return urlunparse(parsed._replace(query=new_query))


def _make_engine(url: str):
    if url.startswith("sqlite"):
        return create_async_engine(url, echo=False)

    is_local = "localhost" in url or "127.0.0.1" in url
    connect_args = {} if is_local else {"ssl": ssl.create_default_context()}

    return create_async_engine(
        url,
        echo=False,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        connect_args=connect_args,
    )


_engine           = None
AsyncSessionLocal = None


def init_engine():
    global _engine, AsyncSessionLocal
    from config import config
    url     = _clean_url(config.DATABASE_URL)
    _engine = _make_engine(url)
    AsyncSessionLocal = async_sessionmaker(
        _engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    return _engine


async def init_db():
    engine = _engine or init_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await _auto_migrate(engine)
    print("✅ Database tayyor!")


async def _auto_migrate(engine):
    """Eski DB ga yangi ustunlar qo'shish va NOT NULL cheklovlarini olib tashlash."""
    async with engine.begin() as conn:

        # 1. Yangi ustunlar qo'shish
        new_columns = [
            ("purchases",  "is_used",       "BOOLEAN DEFAULT FALSE"),
        ("questions", "question_type", "VARCHAR(20) DEFAULT 'choice'"),
            ("questions", "written_parts", "INTEGER DEFAULT 1"),
            ("questions", "keywords_1",    "TEXT"),
            ("questions", "keywords_2",    "TEXT"),
        ]
        for table, col, col_type in new_columns:
            exists = await conn.scalar(
                text("SELECT COUNT(*) FROM information_schema.columns "
                     "WHERE table_name = :t AND column_name = :c"),
                {"t": table, "c": col}
            )
            if not exists:
                await conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}"))
                print(f"✅ Migration: {table}.{col} qo'shildi")

        # 2. user_wrong_questions jadvali (agar yo'q bo'lsa create_all qo'shadi, lekin ustunlarni tekshiramiz)
        wrong_exists = await conn.scalar(
            text("SELECT COUNT(*) FROM information_schema.tables "
                 "WHERE table_name = 'user_wrong_questions'")
        )
        if not wrong_exists:
            await conn.execute(text("""
                CREATE TABLE user_wrong_questions (
                    id SERIAL PRIMARY KEY,
                    telegram_id BIGINT NOT NULL REFERENCES users(telegram_id),
                    question_id INTEGER NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
                    wrong_count INTEGER DEFAULT 1,
                    last_wrong TIMESTAMP DEFAULT NOW(),
                    UNIQUE(telegram_id, question_id)
                )
            """))
            print("✅ Migration: user_wrong_questions jadvali yaratildi")

        # 3. Yozma savollar uchun option_a/b/c/d NOT NULL olib tashlash
        nullable_cols = ["option_a", "option_b", "option_c", "option_d", "correct_answer"]
        for col in nullable_cols:
            is_nullable = await conn.scalar(
                text("SELECT is_nullable FROM information_schema.columns "
                     "WHERE table_name = 'questions' AND column_name = :c"),
                {"c": col}
            )
            if is_nullable == "NO":
                await conn.execute(text(f"ALTER TABLE questions ALTER COLUMN {col} DROP NOT NULL"))
                print(f"✅ Migration: questions.{col} NOT NULL olib tashlandi")