"""
Attestatsiya bo'limlari uchun JSON fayllarni generatsiya qilish.

Ishlatish:
    python generate_json.py

Bu skript VPS da ishga tushiriladi va bolim_1.json ... bolim_10.json
fayllarini GitHub Pages repo papkasiga (yoki joriy papkaga) yozadi.

.env da GITHUB_PAGES_DIR yo'q bo'lsa — joriy papkaga yozadi.
"""
import asyncio, sys, os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# .env ni o'qish
env_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                os.environ.setdefault(k.strip(), v.strip())

# JSON fayllar saqlanadigan papka
# .env da GITHUB_PAGES_DIR bo'lmasa — joriy papka (repo ildizi)
pages_dir = os.getenv('GITHUB_PAGES_DIR', os.path.dirname(os.path.abspath(__file__)))
os.environ['GITHUB_PAGES_DIR'] = pages_dir

print(f"📁 JSON fayllar papkasi: {pages_dir}")

from database.connection import init_engine, init_db
from handlers.question_editor import generate_bolim_json


async def main():
    init_engine()
    await init_db()

    success = 0
    for i in range(1, 11):
        try:
            ok = await generate_bolim_json(i)
            if ok:
                success += 1
                print(f"  ✅ bolim_{i}.json")
            else:
                print(f"  ⚠️  bolim_{i}.json — GITHUB_PAGES_DIR yo'q")
        except Exception as e:
            print(f"  ❌ bolim_{i}.json — {e}")

    print(f"\n✅ {success}/10 ta JSON fayl yaratildi.")
    print(f"📌 Endi fayllarni git ga qo'shing:")
    print(f"   git add bolim_*.json")
    print(f"   git commit -m 'add: attestatsiya JSON fayllar'")
    print(f"   git push")


asyncio.run(main())