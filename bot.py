import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from config import BOT_TOKEN
from handlers import meta, movies, sync, admin
from middleware.subscription import SubscriptionMiddleware
from database import init_db

async def main():
    logging.basicConfig(level=logging.INFO)
    
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
