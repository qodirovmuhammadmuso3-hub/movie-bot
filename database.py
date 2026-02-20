from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGODB_URI, DB_NAME, ADMIN_ID
import datetime

import certifi
client = AsyncIOMotorClient(MONGODB_URI, tlsCAFile=certifi.where(), serverSelectionTimeoutMS=5000)
db = client[DB_NAME]
movies_collection = db["movies"]
users_collection = db["users"]

async def init_db():
    # Title bo'yicha qidiruvni tezlashtirish uchun indeks yaratamiz
    await movies_collection.create_index([("title", "text")])
    # Kod bo'yicha qidiruvni tezlashtirish (unikal bo'lishi shart)
    await movies_collection.create_index("movie_code", unique=True)
    # Foydalanuvchilar IDsi unikal bo'lishi kerak
    await users_collection.create_index("user_id", unique=True)
    # Content type bo'yicha indeks
    await movies_collection.create_index("content_type")
    
    # Eskidan qolgan ma'lumotlarga content_type belgilash (faqat kerak bo'lsa)
    exists = await movies_collection.find_one({"content_type": {"$exists": False}})
    if exists:
        from config import ANIME_CHANNEL
        # Animelarni ajratib olish
        await movies_collection.update_many(
            {"content_type": {"$exists": False}, "source_channel": ANIME_CHANNEL},
            {"$set": {"content_type": "anime"}}
        )
        # Qolganlarini "movie" qilish
        await movies_collection.update_many(
            {"content_type": {"$exists": False}},
            {"$set": {"content_type": "movie"}}
        )

async def get_next_movie_code(content_type="movie"):
    """
    content_type: 'movie' yoki 'anime'
    movie: 001, 002...
    anime: 1, 2...
    """
    pipeline = [
        {"$match": {"content_type": content_type}},
        {"$project": {"code_int": {"$toInt": "$movie_code"}}},
        {"$sort": {"code_int": -1}},
        {"$limit": 1}
    ]
    cursor = movies_collection.aggregate(pipeline)
    result = await cursor.to_list(length=1)
    
    if not result:
        return "001" if content_type == "movie" else "1"
    
    next_val = result[0]["code_int"] + 1
    
    if content_type == "movie":
        return str(next_val).zfill(3)
    return str(next_val)

async def add_user(user_id, full_name, username):
    await users_collection.update_one(
        {"user_id": user_id},
        {"$set": {
            "full_name": full_name,
            "username": username,
            "last_active": datetime.datetime.utcnow()
        }},
        upsert=True
    )

async def get_stats():
    total_users = await users_collection.count_documents({})
    total_movies = await movies_collection.count_documents({})
    return total_users, total_movies

async def get_all_users():
    cursor = users_collection.find({}, {"user_id": 1})
    return await cursor.to_list(length=None)

async def add_movie(movie_code, title, year, genre, duration, file_id, post_link, source_channel, is_series=False, episode_number=None, content_type="movie", media_type="video"):
    # Kino bo'lsa raqamni padding qilamiz (001 formatiga)
    search_code = str(movie_code).strip()
    if content_type == "movie" and search_code.isdigit() and len(search_code) < 3:
        search_code = search_code.zfill(3)
        
    movie_doc = {
        "movie_code": search_code,
        "title": title.strip(),
        "release_year": year,
        "genre": genre,
        "duration": duration,
        "file_id": file_id,
        "post_link": post_link,
        "source_channel": source_channel,
        "is_series": is_series,
        "episode_number": episode_number,
        "content_type": content_type,
        "media_type": media_type,
        "date_added": datetime.datetime.utcnow(),
        "request_count": 0
    }
    await movies_collection.insert_one(movie_doc)

async def get_episodes(title):
    cursor = movies_collection.find({"title": title.strip(), "is_series": True}).sort("episode_number", 1)
    return await cursor.to_list(length=None)

async def get_movie_by_code(code: str, content_type: str | None = None):
    search_code = str(code).strip()
    
    # 1. Qat'iy qidiruv
    query = {"movie_code": search_code}
    if content_type:
        query["content_type"] = content_type
    
    res = await movies_collection.find_one(query)
    
    # 2. Agar movie qidirilayotgan bo'lsa va topilmasa, padding qilib ko'ramiz
    if not res and (not content_type or content_type == "movie") and search_code.isdigit() and len(search_code) < 3:
        padded_code = search_code.zfill(3)
        res = await movies_collection.find_one({"movie_code": padded_code, "content_type": "movie"})
        
    # 3. Agar hali ham topilmasa va content_type berilmagan bo'lsa, har qandayini qidiramiz
    if not res and not content_type:
        res = await movies_collection.find_one({"movie_code": search_code})
            
    return res

async def search_movies(query, content_type=None):
    filter_query = {"title": {"$regex": query, "$options": "i"}}
    if content_type:
        filter_query["content_type"] = content_type
    cursor = movies_collection.find(filter_query)
    return await cursor.to_list(length=10)

async def increment_request_count(movie_code):
    await movies_collection.update_one(
        {"movie_code": str(movie_code)},
        {"$inc": {"request_count": 1}}
    )

async def get_latest_movies(limit=10):
    cursor = movies_collection.find().sort("date_added", -1).limit(limit)
    movies = await cursor.to_list(length=limit)
    return [(m["title"], m["movie_code"]) for m in movies]

async def get_top_movies(limit=10):
    cursor = movies_collection.find().sort("request_count", -1).limit(limit)
    movies = await cursor.to_list(length=limit)
    return [(m["title"], m["movie_code"]) for m in movies]

async def update_movie_field(movie_code, update_data):
    """Bazadagi kontent ma'lumotlarini yangilash."""
    await movies_collection.update_one(
        {"movie_code": str(movie_code)},
        {"$set": update_data}
    )
