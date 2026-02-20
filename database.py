import asyncpg
import datetime
import asyncio
import dns.resolver
import os
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
ADMIN_ID = os.getenv("ADMIN_ID")

# DNS muammosini hal qilish uchun Google DNS ishlatamiz
def setup_dns():
    try:
        import dns.resolver
        dns.resolver.default_resolver = dns.resolver.Resolver(configure=False)
        dns.resolver.default_resolver.nameservers = ['8.8.8.8', '8.8.4.4']
    except Exception as e:
        print(f"DNS setup error (not critical): {e}")

setup_dns()

pool = None

async def get_pool():
    global pool
    if pool is None:
        pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=10)
    return pool

async def init_db():
    p = await get_pool()
    async with p.acquire() as conn:
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id BIGINT PRIMARY KEY,
                full_name TEXT,
                username TEXT,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS movies (
                movie_code TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                release_year TEXT,
                genre TEXT,
                duration TEXT,
                file_id TEXT NOT NULL,
                post_link TEXT,
                source_channel TEXT,
                is_series BOOLEAN DEFAULT FALSE,
                episode_number INTEGER,
                content_type TEXT DEFAULT 'movie',
                media_type TEXT DEFAULT 'video',
                date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                request_count INTEGER DEFAULT 0
            )
        ''')

async def get_next_movie_code(content_type="movie"):
    p = await get_pool()
    async with p.acquire() as conn:
        row = await conn.fetchrow('''
            SELECT movie_code FROM movies 
            WHERE content_type = $1 AND movie_code ~ '^[0-9]+$'
            ORDER BY movie_code::INTEGER DESC LIMIT 1
        ''', content_type)
        
        if not row:
            return "001" if content_type == "movie" else "1"
        
        last_code = int(row['movie_code'])
        next_val = last_code + 1
        if content_type == "movie":
            return str(next_val).zfill(3)
        return str(next_val)

async def add_user(user_id, full_name, username):
    p = await get_pool()
    async with p.acquire() as conn:
        await conn.execute('''
            INSERT INTO users (user_id, full_name, username, last_active)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (user_id) DO UPDATE SET
                full_name = EXCLUDED.full_name,
                username = EXCLUDED.username,
                last_active = EXCLUDED.last_active
        ''', user_id, full_name, username, datetime.datetime.utcnow())

async def get_stats():
    p = await get_pool()
    async with p.acquire() as conn:
        total_users = await conn.fetchval('SELECT COUNT(*) FROM users')
        total_movies = await conn.fetchval('SELECT COUNT(*) FROM movies')
        return total_users, total_movies

async def get_all_users():
    p = await get_pool()
    async with p.acquire() as conn:
        rows = await conn.fetch('SELECT user_id FROM users')
        return [dict(row) for row in rows]

async def add_movie(movie_code, title, year, genre, duration, file_id, post_link, source_channel, is_series=False, episode_number=None, content_type="movie", media_type="video"):
    search_code = str(movie_code).strip()
    if content_type == "movie" and search_code.isdigit() and len(search_code) < 3:
        search_code = search_code.zfill(3)
    
    p = await get_pool()
    async with p.acquire() as conn:
        await conn.execute('''
            INSERT INTO movies (
                movie_code, title, release_year, genre, duration, file_id, post_link, source_channel, 
                is_series, episode_number, content_type, media_type, date_added, request_count
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
            ON CONFLICT (movie_code) DO NOTHING
        ''', search_code, title.strip(), year, genre, duration, file_id, post_link, source_channel,
              is_series, episode_number, content_type, media_type, datetime.datetime.utcnow(), 0)

async def get_episodes(title):
    p = await get_pool()
    async with p.acquire() as conn:
        rows = await conn.fetch('''
            SELECT * FROM movies WHERE title = $1 AND is_series = TRUE ORDER BY episode_number ASC
        ''', title.strip())
        return [dict(row) for row in rows]

async def get_movie_by_code(code: str, content_type: str | None = None):
    search_code = str(code).strip()
    p = await get_pool()
    async with p.acquire() as conn:
        if content_type:
            row = await conn.fetchrow('SELECT * FROM movies WHERE movie_code = $1 AND content_type = $2', search_code, content_type)
        else:
            row = await conn.fetchrow('SELECT * FROM movies WHERE movie_code = $1', search_code)
        
        if row:
            return dict(row)
        
        # Padding search
        if (not content_type or content_type == "movie") and search_code.isdigit() and len(search_code) < 3:
            padded_code = search_code.zfill(3)
            row = await conn.fetchrow('SELECT * FROM movies WHERE movie_code = $1 AND content_type = \'movie\'', padded_code)
            if row:
                return dict(row)
                
    return None

async def search_movies(query, content_type=None):
    p = await get_pool()
    async with p.acquire() as conn:
        sql = 'SELECT * FROM movies WHERE title ILIKE $1'
        params = [f'%{query}%']
        if content_type:
            sql += ' AND content_type = $2'
            params.append(content_type)
        sql += ' LIMIT 10'
        
        rows = await conn.fetch(sql, *params)
        return [dict(row) for row in rows]

async def increment_request_count(movie_code):
    p = await get_pool()
    async with p.acquire() as conn:
        await conn.execute('UPDATE movies SET request_count = request_count + 1 WHERE movie_code = $1', str(movie_code))

async def get_latest_movies(limit=10):
    p = await get_pool()
    async with p.acquire() as conn:
        rows = await conn.fetch('SELECT title, movie_code FROM movies ORDER BY date_added DESC LIMIT $1', limit)
        return [(row['title'], row['movie_code']) for row in rows]

async def get_top_movies(limit=10):
    p = await get_pool()
    async with p.acquire() as conn:
        rows = await conn.fetch('SELECT title, movie_code FROM movies ORDER BY request_count DESC LIMIT $1', limit)
        return [(row['title'], row['movie_code']) for row in rows]

async def update_movie_field(movie_code, update_data):
    if not update_data:
        return
    p = await get_pool()
    async with p.acquire() as conn:
        set_clauses = [f"{k} = ${i+2}" for i, k in enumerate(update_data.keys())]
        sql = f"UPDATE movies SET {', '.join(set_clauses)} WHERE movie_code = $1"
        params = [str(movie_code)] + list(update_data.values())
        await conn.execute(sql, *params)
