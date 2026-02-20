import asyncio
from database import movies_collection

async def check():
    print("--- MA'LUMOTLAR BAZASI ---")
    cursor = movies_collection.find().sort("date_added", -1)
    movies = await cursor.to_list(length=20)
    for m in movies:
        print(f"KOD: {m.get('movie_code')} | NOMI: {m.get('title')} | TUR: {m.get('content_type')} | KANAL: {m.get('source_channel')}")
    print("--------------------------")

if __name__ == "__main__":
    asyncio.run(check())
