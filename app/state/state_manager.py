import os
import datetime
import uuid
import logging
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("deepbolt.db")


class StateManager:
    def __init__(self):
        db_url = os.getenv("DB_URL")
        if not db_url:
            raise ValueError("DB_URL not found in environment")
        self.client = AsyncIOMotorClient(
            db_url,
            serverSelectionTimeoutMS=10_000,  # Fail fast on connection issues
        )
        self.db = self.client.autocall_db
        self.users = self.db.users
        self.urls = self.db.urls
        logger.info("MongoDB client initialized (db=%s)", self.db.name)

    # User Management
    async def create_user(self, username, hashed_password):
        user_id = str(uuid.uuid4())
        user = {
            "id": user_id,
            "username": username,
            "password": hashed_password,
            "created_at": datetime.datetime.now().isoformat()
        }
        await self.users.insert_one(user)
        user.pop("_id", None)
        return user

    async def get_user_by_username(self, username):
        return await self.users.find_one({"username": username}, {"_id": 0})

    async def get_user_by_id(self, user_id):
        return await self.users.find_one({"id": user_id}, {"_id": 0})

    # URL Management
    async def add_url(self, user_id: str, url: str):
        url_id = str(uuid.uuid4())
        url_doc = {
            "id": url_id,
            "user_id": user_id,
            "url": url,
            "status": "Pending",
            "last_ping": "Never",
            "added_at": datetime.datetime.now().isoformat()
        }
        await self.urls.insert_one(url_doc)
        url_doc.pop("_id", None)
        return url_doc

    async def get_urls(self, user_id: str):
        cursor = self.urls.find({"user_id": user_id}, {"_id": 0})
        return await cursor.to_list(length=100)

    async def delete_url(self, user_id: str, url_id: str):
        result = await self.urls.delete_one({"user_id": user_id, "id": url_id})
        return result.deleted_count > 0

    async def update_url_status(self, url_id: str, status: str, last_ping: str):
        await self.urls.update_one(
            {"id": url_id},
            {"$set": {"status": status, "last_ping": last_ping}}
        )

    async def get_all_tracking_urls(self):
        """Returns list of (user_id, url_id, url) for background pinger"""
        cursor = self.urls.find({})
        urls = await cursor.to_list(length=1000)
        return [(u["user_id"], u["id"], u["url"]) for u in urls]

