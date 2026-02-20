import asyncio
from database import movies_collection, init_db

async def normalize_database():
    await init_db()
    print("Bazani normalizatsiya qilish boshlandi...")
    
    # 1. Dublikatlarni tekshirish va tuzatish
    # Agarda movie_code dublikat bo'lsa, indeks unga xalaqit beradi.
    # Biz indeksni vaqtinchalik olib tashlashimiz yoki ehtiyotkor bo'lishimiz kerak.
    # Lekin eng yaxshisi hamma kinolarni kodsizlantirib, keyin boshidan raqamlash.
    
    cursor = movies_collection.find({"content_type": "movie"}).sort("date_added", 1)
    movies = await cursor.to_list(length=None)
    
    print(f"{len(movies)} ta kino qayta raqamlanmoqda...")
    for i, m in enumerate(movies, 1):
        new_code = str(i).zfill(3)
        await movies_collection.update_one({"_id": m["_id"]}, {"$set": {"movie_code": new_code}})
    
    # 2. Animelarni qayta raqamlash
    cursor = movies_collection.find({"content_type": "anime"}).sort("date_added", 1)
    animes = await cursor.to_list(length=None)
    
    print(f"{len(animes)} ta anime qayta raqamlanmoqda...")
    for i, a in enumerate(animes, 1):
        new_code = str(i)
        await movies_collection.update_one({"_id": a["_id"]}, {"$set": {"movie_code": new_code}})

    print("Normalizatsiya yakunlandi!")

if __name__ == "__main__":
    asyncio.run(normalize_database())
