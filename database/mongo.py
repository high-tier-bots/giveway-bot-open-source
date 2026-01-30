from pymongo import MongoClient
from config import Config

class MongoDB:
    def __init__(self):
        self.client = MongoClient(Config.DB_URL)
        self.db = self.client[Config.DB_NAME]
        
        # Collections
        self.users = self.db.users
        self.giveaways = self.db.giveaways
        self.settings = self.db.settings
        self.chats = self.db.chats
        self.broadcasts = self.db.broadcasts
        
        # Initialize default settings
        self._init_settings()
    
    def _init_settings(self):
        """Initialize default settings if not exists"""
        if not self.settings.find_one({"_id": "main"}):
            self.settings.insert_one({
                "_id": "main",
                "force_subscribe": Config.FORCE_SUBSCRIBE,
                "force_channels": [],
                "log_group_id": Config.LOG_CHANNEL,
                "admins": Config.ADMINS
            })
    
    def close(self):
        self.client.close()

# Global database instance
db = MongoDB()
