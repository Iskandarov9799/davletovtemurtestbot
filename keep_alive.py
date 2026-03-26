"""
HTTP server — bot ishlayotganini tekshirish uchun.
"""
import logging
from aiohttp import web

logger = logging.getLogger(__name__)

async def health_check(request):
    return web.Response(text="✅ Bot ishlayapti!", status=200)

def create_app():
    app = web.Application()
    app.router.add_get("/", health_check)
    app.router.add_get("/health", health_check)
    return app