"""
Render.com "uxlab qolmasligi" uchun HTTP server.
Miniapp fayllarini ham serve qiladi — alohida hosting kerak emas.
"""
from aiohttp import web
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# index.html qayerda ekanligini avtomatik aniqlash
if os.path.exists(os.path.join(BASE_DIR, "index.html")):
    MINIAPP_DIR = BASE_DIR                          # asosiy papkada
elif os.path.exists(os.path.join(BASE_DIR, "miniapp", "index.html")):
    MINIAPP_DIR = os.path.join(BASE_DIR, "miniapp") # miniapp/ papkada
else:
    MINIAPP_DIR = None

async def health_check(request):
    return web.Response(text="✅ Bot ishlayapti!", status=200)

async def serve_index(request):
    return web.FileResponse(os.path.join(MINIAPP_DIR, "index.html"))

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", health_check)
    app.router.add_get("/health", health_check)

    if MINIAPP_DIR:
        app.router.add_get("/miniapp", serve_index)
        app.router.add_get("/miniapp/", serve_index)
        app.router.add_static("/miniapp/", path=MINIAPP_DIR, name="miniapp")
        print(f"📱 Miniapp papka: {MINIAPP_DIR}")
    else:
        print("⚠️  index.html topilmadi — miniapp serve qilinmaydi")

    runner = web.AppRunner(app)
    await runner.setup()

    site = web.TCPSite(runner, "0.0.0.0", 8080)
    await site.start()
    print("🌐 Web server port 8080 da ishga tushdi")