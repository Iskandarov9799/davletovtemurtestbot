"""
HTTP server — bot bilan parallel ishlaydi.
/result endpoint — miniapp natijalarini qabul qiladi.
"""
import json
import logging
from aiohttp import web

logger = logging.getLogger(__name__)

async def health_check(request):
    return web.Response(text="✅ Bot ishlayapti!", status=200)

async def receive_result(request):
    """
    Miniapp natijasini qabul qiladi va botga yuboradi.
    POST /result
    Body: { user_id, correct, wrong, skip, total, score, subject, ... }
    """
    try:
        data = await request.json()
        user_id = data.get('user_id')
        if not user_id:
            return web.json_response({'ok': False, 'error': 'user_id yo\'q'}, status=400)

        # Bot ga yuborish
        from aiogram import Bot
        from config import config
        from database.db import save_test_result, mark_wrong_question, mark_correct_question

        correct = data.get('correct', 0)
        wrong   = data.get('wrong', 0)
        skipped = data.get('skip', 0)
        total   = data.get('total', 0)
        pct     = data.get('score', 0)

        # DB ga saqlash
        try:
            await save_test_result(
                telegram_id=int(user_id),
                subject=data.get('subject', 'adabiyot'),
                category=data.get('category', 'aralash'),
                subcategory=data.get('subcategory'),
                difficulty=None,
                correct=correct, wrong=wrong, skipped=skipped,
                is_attestation=data.get('is_attestation', False)
            )
        except Exception as e:
            logger.error(f"save_test_result xato: {e}")

        # Xato/to'g'ri savollarni saqlash
        for qid in data.get('wrong_ids', []):
            try:
                await mark_wrong_question(int(user_id), int(qid))
            except Exception:
                pass
        for qid in data.get('correct_ids', []):
            try:
                await mark_correct_question(int(user_id), int(qid))
            except Exception:
                pass

        # Foydalanuvchiga natija xabari
        if pct >= 90:   grade, emoji = "A'lo (5)",      "🏆"
        elif pct >= 70: grade, emoji = "Yaxshi (4)",     "🎉"
        elif pct >= 50: grade, emoji = "Qoniqarli (3)",  "📚"
        else:           grade, emoji = "Qoniqarsiz (2)", "😔"

        # Global singleton — har safar yangi Bot yaratmaslik uchun (connection leak oldini olish)
        if not hasattr(receive_result, '_bot') or receive_result._bot is None:
            receive_result._bot = Bot(token=config.BOT_TOKEN)
        bot = receive_result._bot
        try:
            from keyboards.keyboards import main_menu_keyboard
            await bot.send_message(
                chat_id=int(user_id),
                text=(
                    f"{emoji} <b>Test natijasi!</b>\n\n"
                    f"━━━━━━━━━━━━━\n"
                    f"✅ To'g'ri:    <b>{correct}/{total}</b>\n"
                    f"❌ Xato:       <b>{wrong}/{total}</b>\n"
                    f"⏭ O'tkazildi: <b>{skipped}</b>\n"
                    f"📈 Ball:       <b>{pct}%</b>\n"
                    f"🎓 Baho:       <b>{grade}</b>\n"
                    f"━━━━━━━━━━━━━"
                ),
                reply_markup=main_menu_keyboard(),
                parse_mode="HTML"
            )

            # Guruhga yuborish
            if config.RESULT_GROUP_ID:
                uname = data.get('username', str(user_id))
                SUBJ = {'onatili': '📚 Ona tili', 'adabiyot': '📖 Adabiyot',
                        'attestation': '🎓 Attestatsiya', 'milliy': '🏅 Milliy'}
                subj_label = SUBJ.get(data.get('subject', ''), data.get('subject', ''))
                await bot.send_message(
                    chat_id=int(config.RESULT_GROUP_ID),
                    text=f"{emoji} <b>{uname}</b> — {subj_label}\n✅ {correct}/{total}  |  📈 {pct}%  |  🎓 {grade}",
                    parse_mode="HTML"
                )
        except Exception:
            pass

        return web.json_response({'ok': True})

    except Exception as e:
        logger.error(f"receive_result xato: {e}")
        return web.json_response({'ok': False, 'error': str(e)}, status=500)

async def serve_miniapp(request):
    import os
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    index_path = os.path.join(BASE_DIR, "index.html")
    if os.path.exists(index_path):
        return web.FileResponse(index_path)
    return web.Response(text="index.html topilmadi", status=404)

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", health_check)
    app.router.add_get("/health", health_check)
    app.router.add_post("/result", receive_result)

    import os
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    for fname in ["index.html", "main.js", "style.css"]:
        fpath = os.path.join(BASE_DIR, fname)
        if os.path.exists(fpath):
            app.router.add_get(f"/{fname}", lambda r, p=fpath: web.FileResponse(p))

    runner = web.AppRunner(app)
    await runner.setup()

    site = web.TCPSite(runner, "0.0.0.0", 8080)
    await site.start()
    print("🌐 Web server port 8080 da ishga tushdi")
    print("📡 /result endpoint faol")