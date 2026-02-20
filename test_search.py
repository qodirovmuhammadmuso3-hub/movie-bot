import asyncio
from database import get_movie_by_code, search_movies

async def test():
    print("=== KOD BO'YICHA QIDIRUV ===")
    r = await get_movie_by_code("001")
    print(f"001 -> {r}")
    
    r2 = await get_movie_by_code("1")
    print(f"1 -> {r2}")
    
    r3 = await get_movie_by_code("9")
    print(f"9 -> {r3}")
    
    r4 = await get_movie_by_code("009")
    print(f"009 -> {r4}")
    
    print("\n=== ISM BO'YICHA QIDIRUV ===")
    s = await search_movies("Kino")
    print(f"'Kino' -> {len(s)} ta natija: {[x.get('title') for x in s]}")

asyncio.run(test())
