from pymongo import MongoClient
from config import Config
import time

class MongoDB:
    def __init__(self):
        try:
            # Connect with timeout and retry settings
            self.client = MongoClient(
                Config.DB_URL,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=10000,
                socketTimeoutMS=None
            )
            # Force connection test
            self.client.server_info()
            
            self.db = self.client[Config.DB_NAME]
            
            # Collections
            self.users = self.db.users
            self.giveaways = self.db.giveaways
            self.settings = self.db.settings
            self.chats = self.db.chats
            self.broadcasts = self.db.broadcasts
            
            # Initialize default settings
            self._init_settings()
        except Exception as e:
            print(f"[ERROR] Failed to connect to MongoDB: {e}")
            raise
    
    def _init_settings(self):
        """Initialize default settings if not exists"""
        try:
            if not self.settings.find_one({"_id": "main"}):
                self.settings.insert_one({
                    "_id": "main",
                    "force_subscribe": Config.FORCE_SUBSCRIBE,
                    "force_channels": [],
                    "log_group_id": Config.LOG_CHANNEL,
                    "admins": Config.ADMINS
                })
        except Exception as e:
            print(f"[ERROR] Failed to initialize settings: {e}")
    
    def close(self):
        try:
            self.client.close()
        except Exception as e:
            print(f"[ERROR] Failed to close database: {e}")

# Global database instance
try:
    db = MongoDB()
except Exception as e:
    print(f"[CRITICAL] Cannot start without database connection: {e}")
    raise
