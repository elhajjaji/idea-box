from motor.motor_asyncio import AsyncIOMotorClient
from odmantic import AIOEngine
import os

class Database:
    client: AsyncIOMotorClient = None
    engine: AIOEngine = None

    @staticmethod
    async def connect(mongo_uri: str = None, db_name: str = None):
        if mongo_uri is None:
            mongo_uri = os.getenv("MONGO_URI")
        if db_name is None:
            db_name = os.getenv("MONGO_DB_NAME", "boiteaidees")

        Database.client = AsyncIOMotorClient(mongo_uri)
        Database.engine = AIOEngine(client=Database.client, database=db_name)

    @staticmethod
    async def close():
        if Database.client:
            Database.client.close()
