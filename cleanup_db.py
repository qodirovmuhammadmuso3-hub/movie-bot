import asyncio
from database import get_pool, init_db

async def normalize_database():
    print("\n" + "="*50)
    print("SKRIPT ISHGA TUSHDI: POSTGRESQL VERSIYASI")
    print("="*50 + "\n")
    await init_db()
    
    p = await get_pool()
    async with p.acquire() as conn:
        # 1. Kinolarni qayta raqamlash (content_type = 'movie')
        movies = await conn.fetch('''
            SELECT movie_code, title, date_added FROM movies 
            WHERE content_type = 'movie' 
            ORDER BY date_added ASC
        ''')
        
        print(f"{len(movies)} ta kino qayta raqamlanmoqda...")
        for i, m in enumerate(movies, 1):
            new_code = str(i).zfill(3)
            await conn.execute('''
                UPDATE movies SET movie_code = $1 WHERE title = $2 AND content_type = 'movie'
            ''', new_code, m['title'])
        
        # 2. Animelarni qayta raqamlash (content_type = 'anime')
        animes = await conn.fetch('''
            SELECT movie_code, title, date_added FROM movies 
            WHERE content_type = 'anime' 
            ORDER BY date_added ASC
        ''')
        
        print(f"{len(animes)} ta anime qayta raqamlanmoqda...")
        for i, a in enumerate(animes, 1):
            new_code = str(i)
            await conn.execute('''
                UPDATE movies SET movie_code = $1 WHERE title = $2 AND content_type = 'anime'
            ''', new_code, a['title'])

    print("Normalizatsiya yakunlandi!")

if __name__ == "__main__":
    asyncio.run(normalize_database())
