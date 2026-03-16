"""
PostgreSQL migration — yangi ustunlarni qo'shish.
Render consolida bir marta ishga tushiring:
    python migrate_pg.py
"""
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

async def migrate():
    import asyncpg

    url = os.getenv("DATABASE_URL", "")
    # asyncpg uchun postgresql:// formatiga o'tkazish
    url = url.replace("postgresql+asyncpg://", "postgresql://")
    url = url.replace("postgres://", "postgresql://")

    print(f"🔌 Ulanmoqda...")
    conn = await asyncpg.connect(url)

    migrations = [
        # questions jadvaliga yangi ustunlar
        ("question_type",  "ALTER TABLE questions ADD COLUMN question_type  VARCHAR(20) DEFAULT 'choice'"),
        ("written_parts",  "ALTER TABLE questions ADD COLUMN written_parts  INTEGER     DEFAULT 1"),
        ("keywords_1",     "ALTER TABLE questions ADD COLUMN keywords_1     TEXT"),
        ("keywords_2",     "ALTER TABLE questions ADD COLUMN keywords_2     TEXT"),
    ]

    for col_name, sql in migrations:
        # Ustun mavjudligini tekshirish
        exists = await conn.fetchval("""
            SELECT COUNT(*) FROM information_schema.columns
            WHERE table_name = 'questions' AND column_name = $1
        """, col_name)

        if exists:
            print(f"ℹ️  questions.{col_name} — allaqachon mavjud, o'tkazib yuborildi")
        else:
            await conn.execute(sql)
            print(f"✅ questions.{col_name} — qo'shildi!")

    await conn.close()
    print("\n✅ Migration muvaffaqiyatli tugadi!")

if __name__ == "__main__":
    asyncio.run(migrate())