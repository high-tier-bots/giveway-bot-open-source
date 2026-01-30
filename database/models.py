from datetime import datetime
from database.mongo import db

class User:
    @staticmethod
    def add_user(user_id, username=None, referred_by=None):
        """Add a new user to database"""
        if not db.users.find_one({"user_id": user_id}):
            user_data = {
                "user_id": user_id,
                "username": username,
                "joined_at": datetime.now(),
                "referrals": [],
                "referred_by": referred_by
            }
            db.users.insert_one(user_data)
            
            # Update referrer's referrals
            if referred_by:
                db.users.update_one(
                    {"user_id": referred_by},
                    {"$push": {"referrals": user_id}}
                )
            return True
        return False
    
    @staticmethod
    def get_user(user_id):
        """Get user by ID"""
        return db.users.find_one({"user_id": user_id})
    
    @staticmethod
    def get_all_users():
        """Get all users"""
        return list(db.users.find({}))
    
    @staticmethod
    def count_users():
        """Count total users"""
        return db.users.count_documents({})

class Giveaway:
    @staticmethod
    def create_giveaway(giveaway_id, prize, description, end_time, winners_count, created_by):
        """Create a new giveaway"""
        giveaway_data = {
            "giveaway_id": giveaway_id,
            "prize": prize,
            "description": description,
            "end_time": end_time,
            "winners_count": winners_count,
            "status": "active",
            "participants": [],
            "winners": [],
            "created_by": created_by,
            "created_at": datetime.now()
        }
        db.giveaways.insert_one(giveaway_data)
        return giveaway_data
    
    @staticmethod
    def add_participant(giveaway_id, user_id):
        """Add participant to giveaway"""
        giveaway = db.giveaways.find_one({"giveaway_id": giveaway_id})
        if giveaway and user_id not in giveaway.get("participants", []):
            db.giveaways.update_one(
                {"giveaway_id": giveaway_id},
                {"$push": {"participants": user_id}}
            )
            return True
        return False
    
    @staticmethod
    def get_active_giveaway():
        """Get active giveaway"""
        return db.giveaways.find_one({"status": "active"})
    
    @staticmethod
    def get_giveaway(giveaway_id):
        """Get giveaway by ID"""
        return db.giveaways.find_one({"giveaway_id": giveaway_id})
    
    @staticmethod
    def end_giveaway(giveaway_id, winners=None):
        """End a giveaway"""
        update_data = {"status": "ended"}
        if winners:
            update_data["winners"] = winners
        db.giveaways.update_one(
            {"giveaway_id": giveaway_id},
            {"$set": update_data}
        )
    
    @staticmethod
    def get_participants_count(giveaway_id):
        """Get participants count"""
        giveaway = db.giveaways.find_one({"giveaway_id": giveaway_id})
        return len(giveaway.get("participants", [])) if giveaway else 0

class Settings:
    @staticmethod
    def get_settings():
        """Get bot settings"""
        settings = db.settings.find_one({"_id": "main"})
        return settings if settings else {}
    
    @staticmethod
    def update_setting(key, value):
        """Update a setting"""
        db.settings.update_one(
            {"_id": "main"},
            {"$set": {key: value}},
            upsert=True
        )
    
    @staticmethod
    def add_force_channel(channel_id, channel_username):
        """Add a force subscribe channel"""
        db.settings.update_one(
            {"_id": "main"},
            {"$addToSet": {"force_channels": {"id": channel_id, "username": channel_username}}}
        )
    
    @staticmethod
    def remove_force_channel(channel_id):
        """Remove a force subscribe channel"""
        db.settings.update_one(
            {"_id": "main"},
            {"$pull": {"force_channels": {"id": channel_id}}}
        )
    
    @staticmethod
    def get_force_channels():
        """Get all force subscribe channels"""
        settings = Settings.get_settings()
        return settings.get("force_channels", [])
    
    @staticmethod
    def add_admin(admin_id):
        """Add an admin"""
        db.settings.update_one(
            {"_id": "main"},
            {"$addToSet": {"admins": admin_id}}
        )
    
    @staticmethod
    def remove_admin(admin_id):
        """Remove an admin"""
        db.settings.update_one(
            {"_id": "main"},
            {"$pull": {"admins": admin_id}}
        )
    
    @staticmethod
    def get_admins():
        """Get all admins"""
        settings = Settings.get_settings()
        return settings.get("admins", [])

class Chat:
    @staticmethod
    def add_chat(chat_id, chat_type, added_by):
        """Add a chat (group/channel)"""
        if not db.chats.find_one({"chat_id": chat_id}):
            # Convert enum to string if needed
            if hasattr(chat_type, 'value'):
                chat_type = chat_type.value
            chat_data = {
                "chat_id": chat_id,
                "type": chat_type,
                "added_by": added_by,
                "date_added": datetime.now()
            }
            db.chats.insert_one(chat_data)
            return True
        return False
    
    @staticmethod
    def get_all_chats(chat_type=None):
        """Get all chats, optionally filtered by type"""
        query = {"type": chat_type} if chat_type else {}
        return list(db.chats.find(query))
    
    @staticmethod
    def count_chats(chat_type=None):
        """Count chats by type"""
        query = {"type": chat_type} if chat_type else {}
        return db.chats.count_documents(query)

class Broadcast:
    @staticmethod
    def add_broadcast(message, target_type, sent_by, success_count, failed_count):
        """Add broadcast history"""
        broadcast_data = {
            "message": message,
            "target_type": target_type,
            "sent_by": sent_by,
            "date": datetime.now(),
            "success_count": success_count,
            "failed_count": failed_count
        }
        db.broadcasts.insert_one(broadcast_data)
