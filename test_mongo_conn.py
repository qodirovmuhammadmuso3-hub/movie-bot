import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv
import certifi
import dns.resolver

# DNS muammosini hal qilish uchun Google DNS ishlatamiz
dns.resolver.default_resolver = dns.resolver.Resolver(configure=False)
dns.resolver.default_resolver.nameservers = ['8.8.8.8']

load_dotenv()

async def test_conn():
    uri = os.getenv("MONGODB_URI")
    print(f"Connecting to: {uri[:20]}...")
    client = AsyncIOMotorClient(uri, serverSelectionTimeoutMS=5000, tlsCAFile=certifi.where())
    try:
        await client.admin.command('ping')
        print("Muvaffaqiyatli ulandi! (Connected successfully)")
    except Exception as e:
        print(f"Xatolik yuz berdi: {e}")

if __name__ == "__main__":
    asyncio.run(test_conn())
