from pyrogram import Client
from pyrogram.types import Message
from pyrogram.errors import UserNotParticipant, ChatAdminRequired
from database.models import Settings
from keyboards.inline import force_subscribe_keyboard
from utils.logger import logger

class ForceSubscribeService:
    def __init__(self, app: Client):
        self.app = app
    
    async def check_user_subscribed(self, user_id: int) -> tuple[bool, list]:
        """Check if user is subscribed to all force channels"""
        settings = Settings.get_settings()
        force_subscribe_enabled = settings.get("force_subscribe", False)
        
        if not force_subscribe_enabled:
            return True, []
        
        force_channels = Settings.get_force_channels()
        if not force_channels:
            return True, []
        
        not_subscribed = []
        
        for channel in force_channels:
            # Handle both old format (int) and new format (dict)
            if isinstance(channel, dict):
                channel_id = channel.get("id")
            else:
                # Old format - just an integer
                channel_id = channel
                
            try:
                member = await self.app.get_chat_member(channel_id, user_id)
                if member.status in ["left", "kicked"]:
                    not_subscribed.append(channel)
            except UserNotParticipant:
                not_subscribed.append(channel)
            except Exception as e:
                logger.error(f"Error checking subscription for channel {channel_id}: {e}")
                continue
        
        is_subscribed = len(not_subscribed) == 0
        return is_subscribed, not_subscribed
    
    async def send_force_subscribe_message(self, message: Message, not_subscribed_channels: list):
        """Send force subscribe message with join buttons"""
        text = "⚠️ **You must join the following channels to participate in the giveaway:**\n\n"
        text += "Please join all channels and click '✅ Try Again'"
        
        keyboard = force_subscribe_keyboard(not_subscribed_channels)
        await message.reply_text(text, reply_markup=keyboard)
    
    async def validate_channel(self, channel_id: int) -> tuple[bool, str, str]:
        """Validate if bot is admin in channel and get channel info"""
        try:
            chat = await self.app.get_chat(channel_id)
            
            # Check if bot is admin
            member = await self.app.get_chat_member(channel_id, "me")
            if member.status not in ["administrator", "creator"]:
                return False, None, "Bot is not an administrator in this channel"
            
            # Get username
            username = chat.username if chat.username else None
            if not username:
                return False, None, "Channel must have a public username"
            
            return True, username, None
        
        except ChatAdminRequired:
            return False, None, "Bot needs admin rights in the channel"
        except Exception as e:
            return False, None, str(e)
