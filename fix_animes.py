import asyncio
from database import get_pool, init_db

async def fix_anime_database():
    await init_db()
    print("Bazani tekshirish...")
    
    p = await get_pool()
    async with p.acquire() as conn:
        # 1. 'Anime' kanalidan kelgan barcha kinolarni topish
        # Source channel 'Anime' bo'lgan yoki title da 'Anime' so'zi borlarni tekshiramiz
        animes = await conn.fetch('''
            SELECT title, movie_code FROM movies 
            WHERE source_channel ILIKE '%Anime%' OR title ILIKE '%Anime%'
            ORDER BY date_added ASC
        ''')
        
        print(f"Jami {len(animes)} ta potentsial anime topildi.")
        
        # 2. Ularni 'anime' turiga o'tkazish va 1 dan boshlab kodlash
        for i, anime in enumerate(animes, 1):
            new_code = str(i)
            print(f"Yangilanmoqda: {anime['title']} ({anime['movie_code']} -> {new_code})")
            await conn.execute('''
                UPDATE movies SET content_type = 'anime', movie_code = $1 
                WHERE title = $2
            ''', new_code, anime['title'])
    
    print("Bazani tozalash yakunlandi!")

if __name__ == "__main__":
    asyncio.run(fix_anime_database())
