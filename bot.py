import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from config import BOT_TOKEN
from handlers import meta, movies, sync, admin
from middleware.subscription import SubscriptionMiddleware
from database import init_db

from aiohttp import web
import os

async def handle(request):
    return web.Response(text="Bot is running!")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logging.info(f"Web server started on port {port}")

async def main():
    logging.basicConfig(level=logging.INFO)
    
    # Render'da bot o'chib qolmasligi uchun veb-serverni ishga tushiramiz
    asyncio.create_task(start_web_server())

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    # Register Middlewares
    dp.message.middleware(SubscriptionMiddleware())
    dp.callback_query.middleware(SubscriptionMiddleware())

    # Register Routers
    dp.include_router(admin.router) # Admin router birinchi bo'lishi kerak
    dp.include_router(meta.router)
    dp.include_router(movies.router)
    dp.include_router(sync.router)

    # Initialize Database
    await init_db()

    # Bot buyruqlarini sozlash (Menu tugmasi uchun)
    commands = [
        types.BotCommand(command="start", description="Botni ishga tushirish"),
        types.BotCommand(command="help", description="Yordam va qo'llanma"),
        types.BotCommand(command="admin", description="Admin panel (faqat adminlar uchun)"),
    ]
    await bot.set_my_commands(commands)

    # Start Polling
    logging.info("Bot is starting...")
    while True:
        try:
            await dp.start_polling(bot)
        except Exception as e:
            logging.error(f"Bot polling error: {e}")
            logging.info("Restarting in 5 seconds...")
            await asyncio.sleep(5)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
