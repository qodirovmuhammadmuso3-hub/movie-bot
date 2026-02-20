import asyncio
from database import movies_collection

async def fix_anime_database():
    print("Bazani tekshirish...")
    # 1. 'Anime' kanalidan kelgan barcha movie_doc larni topish
    # (Source channel 'Anime' bo'lgan yoki title da 'Anime' so'zi borlarni tekshiramiz)
    query = {
        "$or": [
            {"source_channel": "Anime"},
            {"title": {"$regex": "Anime", "$options": "i"}}
        ]
    }
    
    cursor = movies_collection.find(query).sort("date_added", 1)
    animes = await cursor.to_list(length=None)
    
    print(f"Jami {len(animes)} ta potentsial anime topildi.")
    
    # 2. Ularni 'anime' turiga o'tkazish va 1 dan boshlab kodlash
    for i, anime in enumerate(animes, 1):
        new_code = str(i)
        print(f"Yangilanmoqda: {anime.get('title')} ({anime.get('movie_code')} -> {new_code})")
        await movies_collection.update_one(
            {"_id": anime["_id"]},
            {"$set": {
                "content_type": "anime",
                "movie_code": new_code
            }}
        )
    
    print("Bazani tozalash yakunlandi!")

if __name__ == "__main__":
    asyncio.run(fix_anime_database())
