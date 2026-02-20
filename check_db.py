import asyncio
from database import get_latest_movies, init_db

async def check():
    print("--- MA'LUMOTLAR BAZASI NI SOZLASH ---")
    await init_db()
    print("Jadvallar yaratildi yoki tekshirildi.")
    
    print("\n--- OXIRGI QO'SHILGAN KINOLAR ---")
    movies = await get_latest_movies(10)
    if not movies:
        print("Baza bo'sh.")
    for title, code in movies:
        print(f"KOD: {code} | NOMI: {title}")
    print("--------------------------")

if __name__ == "__main__":
    asyncio.run(check())
