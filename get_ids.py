import asyncio
import logging
from aiogram import Bot
from config import BOT_TOKEN

async def get_channel_ids():
    bot = Bot(token=BOT_TOKEN)
    print("Bot ma'lumotlarini tekshirish...")
    try:
        me = await bot.get_me()
        print(f"Bot nomi: @{me.username}")
        print("\nDIQQAT! Bot kanallarga admin qilingan bo'lishi va oxirgi marta u yerga post qo'yilgan bo'lishi kerak.")
        print("Botga kelgan oxirgi yangilanishlarni tekshiramiz...")
        
        updates = await bot.get_updates(limit=10)
        channels = {}
        for up in updates:
            chat = None
            if up.channel_post:
                chat = up.channel_post.chat
            elif up.message and up.message.chat.type in ['channel', 'supergroup']:
                chat = up.message.chat
                
            if chat:
                channels[chat.id] = {"title": chat.title, "username": chat.username}
        
        if not channels:
            print("Hozircha yangiliklar yo'q. Iltimos, kanallarda birorta xabar yozing (post qo'ying) va skriptni qayta ishga tushiring.")
        else:
            print("\nTopilgan kanallar:")
            for cid, info in channels.items():
                uname = f" (@{info['username']})" if info['username'] else " (Xususiy kanal)"
                print(f"ID: {cid} | Nomi: {info['title']}{uname}")
                print(f"Tavsiya etilgan .env formati: {cid}|https://t.me/...")
                
    except Exception as e:
        print(f"Xatolik: {e}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(get_channel_ids())
