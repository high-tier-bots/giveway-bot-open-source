#(©)HighTierBots - Bot Notifications Handler

from pyrogram import Client 
from pyrogram.errors import FloodWait
from config import Config
from utils.logger import logger
from datetime import datetime


async def send_bot_start_log(client: Client, user) -> bool:
    """
    Send bot start notification to Config.LOG_CHANNEL
    
    Args:
        client: Pyrogram Client instance
        user: User object from message
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        if not Config.LOG_CHANNEL or Config.LOG_CHANNEL == 0:
            logger.warning("LOG_CHANNEL not configured")
            return False
        
        username = f"@{user.username}" if user.username else "Not Available"
        user_id = user.id if user.id else "Unknown"
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        notification_text = (
            f"🚀 <b>New User Start Bot</b>\n\n"
            f"👤 <b>User ID:</b> <code>{user_id}</code>\n"
            f"👤 <b>Username:</b> {username}\n"
            f"🕒 <b>Time:</b> <code>{timestamp}</code>"
        )
        
        await client.send_message(Config.LOG_CHANNEL, notification_text)
        logger.info(f"Bot start notification sent for user {user_id}")
        return True
        
    except FloodWait as e:
        logger.warning(f"FloodWait error while sending start log: {e.value}s")
        return False
    except Exception as e:
        logger.error(f"Error sending bot start notification: {e}")
        return False


async def send_bot_added_log(client: Client, chat, added_by_user) -> bool:
    """
    Send bot added to group/channel notification to Config.LOG_CHANNEL
    
    Args:
        client: Pyrogram Client instance
        chat: Chat object
        added_by_user: User object who added the bot
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        if not Config.LOG_CHANNEL or Config.LOG_CHANNEL == 0:
            logger.warning("LOG_CHANNEL not configured")
            return False
        
        chat_id = chat.id if chat.id else "Unknown"
        chat_name = chat.title if chat.title else "Unknown"
        chat_username = f"@{chat.username}" if chat.username else "Not Available"
        
        chat_type = "Group"
        if hasattr(chat, 'type'):
            if chat.type == "channel":
                chat_type = "Channel"
            elif chat.type in ["group", "supergroup"]:
                chat_type = "Group"
        
        added_by_id = added_by_user.id if added_by_user.id else "Unknown"
        added_by_username = f"@{added_by_user.username}" if added_by_user.username else "Not Available"
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        notification_text = (
            f"🤖 <b>Bot Added Notification</b>\n\n"
            f"📌 <b>Chat Type:</b> <code>{chat_type}</code>\n"
            f"📌 <b>Chat ID:</b> <code>{chat_id}</code>\n"
            f"📌 <b>Chat Name:</b> <code>{chat_name}</code>\n"
            f"📌 <b>Chat Username:</b> {chat_username}\n\n"
            f"👤 <b>Added By User ID:</b> <code>{added_by_id}</code>\n"
            f"👤 <b>Added By Username:</b> {added_by_username}\n\n"
            f"🕒 <b>Time:</b> <code>{timestamp}</code>"
        )
        
        await client.send_message(Config.LOG_CHANNEL, notification_text)
        logger.info(f"Bot added notification sent for chat {chat_id}")
        return True
        
    except FloodWait as e:
        logger.warning(f"FloodWait error while sending bot added log: {e.value}s")
        return False
    except Exception as e:
        logger.error(f"Error sending bot added notification: {e}")
        return False


async def send_request_approved_log(client: Client, chat, user) -> bool:
    """
    Send join request approved notification to Config.LOG_CHANNEL
    
    Args:
        client: Pyrogram Client instance
        chat: Chat object
        user: User object whose request was approved
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        if not Config.LOG_CHANNEL or Config.LOG_CHANNEL == 0:
            logger.warning("LOG_CHANNEL not configured")
            return False
        
        chat_id = chat.id if chat.id else "Unknown"
        chat_name = chat.title if chat.title else "Unknown"
        
        user_id = user.id if user.id else "Unknown"
        username = f"@{user.username}" if user.username else "Not Available"
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        notification_text = (
            f"✅ <b>Join Request Approved</b>\n\n"
            f"👤 <b>User ID:</b> <code>{user_id}</code>\n"
            f"👤 <b>Username:</b> {username}\n\n"
            f"🏷️ <b>Chat ID:</b> <code>{chat_id}</code>\n"
            f"🏷️ <b>Chat Name:</b> <code>{chat_name}</code>\n\n"
            f"🕒 <b>Time:</b> <code>{timestamp}</code>"
        )
        
        await client.send_message(Config.LOG_CHANNEL, notification_text)
        logger.info(f"Join request approved notification sent for user {user_id}")
        return True
        
    except FloodWait as e:
        logger.warning(f"FloodWait error while sending approved log: {e.value}s")
        return False
    except Exception as e:
        logger.error(f"Error sending join request approved notification: {e}")
        return False


async def send_giveaway_created_log(client: Client, giveaway_id: int, prize: str, winners_count: int, created_by_id: int) -> bool:
    """
    Send giveaway created notification to LOG_GROUP_ID
    
    Args:
        client: Pyrogram Client instance
        giveaway_id: Giveaway ID
        prize: Prize description
        winners_count: Number of winners
        created_by_id: Admin user ID who created giveaway
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        if not Config.LOG_CHANNEL or Config.LOG_CHANNEL == 0:
            return False
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        notification_text = (
            f"🎁 <b>Giveaway Created</b>\n\n"
            f"🎫 <b>Giveaway ID:</b> <code>{giveaway_id}</code>\n"
            f"🏆 <b>Prize:</b> <code>{prize}</code>\n"
            f"🎯 <b>Winners:</b> <code>{winners_count}</code>\n"
            f"👤 <b>Created By:</b> <code>{created_by_id}</code>\n\n"
            f"🕒 <b>Time:</b> <code>{timestamp}</code>"
        )
        
        await client.send_message(Config.LOG_CHANNEL, notification_text)
        logger.info(f"Giveaway created notification sent for giveaway {giveaway_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error sending giveaway created notification: {e}")
        return False


async def send_giveaway_ended_log(client: Client, giveaway_id: int, participants_count: int, winners: list) -> bool:
    """
    Send giveaway ended notification to LOG_GROUP_ID
    
    Args:
        client: Pyrogram Client instance
        giveaway_id: Giveaway ID
        participants_count: Number of participants
        winners: List of winner user IDs
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        if not Config.LOG_CHANNEL or Config.LOG_CHANNEL == 0:
            return False
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        winners_text = ", ".join([f"<code>{w}</code>" for w in winners]) if winners else "None"
        
        notification_text = (
            f"🏁 <b>Giveaway Ended</b>\n\n"
            f"🎫 <b>Giveaway ID:</b> <code>{giveaway_id}</code>\n"
            f"👥 <b>Participants:</b> <code>{participants_count}</code>\n"
            f"🎯 <b>Winners:</b> {winners_text}\n\n"
            f"🕒 <b>Time:</b> <code>{timestamp}</code>"
        )
        
        await client.send_message(Config.LOG_CHANNEL, notification_text)
        logger.info(f"Giveaway ended notification sent for giveaway {giveaway_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error sending giveaway ended notification: {e}")
        return False


async def send_user_joined_giveaway_log(client: Client, user_id: int, username: str, giveaway_id: int) -> bool:
    """
    Send user joined giveaway notification to LOG_GROUP_ID
    
    Args:
        client: Pyrogram Client instance
        user_id: User ID
        username: Username
        giveaway_id: Giveaway ID
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        if not Config.LOG_CHANNEL or Config.LOG_CHANNEL == 0:
            return False
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        username = f"@{username}" if username else "Not Available"
        
        notification_text = (
            f"🎉 <b>User Joined Giveaway</b>\n\n"
            f"👤 <b>User ID:</b> <code>{user_id}</code>\n"
            f"👤 <b>Username:</b> {username}\n"
            f"🎫 <b>Giveaway ID:</b> <code>{giveaway_id}</code>\n\n"
            f"🕒 <b>Time:</b> <code>{timestamp}</code>"
        )
        
        await client.send_message(Config.LOG_CHANNEL, notification_text)
        logger.info(f"User {user_id} joined giveaway {giveaway_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error sending user joined giveaway log: {e}")
        return False


async def send_broadcast_log(client: Client, admin_id: int, total_users: int, success: int, failed: int, blocked: int) -> bool:
    """
    Send broadcast completion notification to LOG_GROUP_ID
    
    Args:
        client: Pyrogram Client instance
        admin_id: Admin user ID who sent broadcast
        total_users: Total users
        success: Number of successful sends
        failed: Number of failed sends
        blocked: Number of blocked users
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        if not Config.LOG_CHANNEL or Config.LOG_CHANNEL == 0:
            return False
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        notification_text = (
            f"📢 <b>Broadcast Completed</b>\n\n"
            f"👤 <b>Admin ID:</b> <code>{admin_id}</code>\n"
            f"👥 <b>Total Users:</b> <code>{total_users}</code>\n"
            f"✅ <b>Success:</b> <code>{success}</code>\n"
            f"❌ <b>Failed:</b> <code>{failed}</code>\n"
            f"🚫 <b>Blocked:</b> <code>{blocked}</code>\n\n"
            f"🕒 <b>Time:</b> <code>{timestamp}</code>"
        )
        
        await client.send_message(Config.LOG_CHANNEL, notification_text)
        logger.info(f"Broadcast log sent by admin {admin_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error sending broadcast log: {e}")
        return False


async def send_admin_action_log(client: Client, admin_id: int, action: str, details: str) -> bool:
    """
    Send admin action notification to LOG_GROUP_ID
    
    Args:
        client: Pyrogram Client instance
        admin_id: Admin user ID
        action: Action performed (e.g., "Channel Added", "Settings Updated")
        details: Details of the action
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        if not Config.LOG_CHANNEL or Config.LOG_CHANNEL == 0:
            return False
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        notification_text = (
            f"⚙️ <b>Admin Action</b>\n\n"
            f"👤 <b>Admin ID:</b> <code>{admin_id}</code>\n"
            f"🔧 <b>Action:</b> <code>{action}</code>\n"
            f"📝 <b>Details:</b> <code>{details}</code>\n\n"
            f"🕒 <b>Time:</b> <code>{timestamp}</code>"
        )
        
        await client.send_message(Config.LOG_CHANNEL, notification_text)
        logger.info(f"Admin action log sent for admin {admin_id}: {action}")
        return True
        
    except Exception as e:
        logger.error(f"Error sending admin action log: {e}")
        return False


async def send_force_channel_added_log(client: Client, channel_id: int, channel_title: str, admin_id: int) -> bool:
    """
    Send force subscribe channel added notification to LOG_GROUP_ID
    
    Args:
        client: Pyrogram Client instance
        channel_id: Channel ID
        channel_title: Channel title
        admin_id: Admin user ID who added channel
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        if not Config.LOG_CHANNEL or Config.LOG_CHANNEL == 0:
            return False
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        notification_text = (
            f"📺 <b>Force Channel Added</b>\n\n"
            f"📌 <b>Channel ID:</b> <code>{channel_id}</code>\n"
            f"📌 <b>Channel Title:</b> <code>{channel_title}</code>\n"
            f"👤 <b>Added By:</b> <code>{admin_id}</code>\n\n"
            f"🕒 <b>Time:</b> <code>{timestamp}</code>"
        )
        
        await client.send_message(Config.LOG_CHANNEL, notification_text)
        logger.info(f"Force channel added: {channel_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error sending force channel added log: {e}")
        return False


async def send_force_channel_removed_log(client: Client, channel_id: int, admin_id: int) -> bool:
    """
    Send force subscribe channel removed notification to LOG_GROUP_ID
    
    Args:
        client: Pyrogram Client instance
        channel_id: Channel ID
        admin_id: Admin user ID who removed channel
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        if not Config.LOG_CHANNEL or Config.LOG_CHANNEL == 0:
            return False
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        notification_text = (
            f"🗑️ <b>Force Channel Removed</b>\n\n"
            f"📌 <b>Channel ID:</b> <code>{channel_id}</code>\n"
            f"👤 <b>Removed By:</b> <code>{admin_id}</code>\n\n"
            f"🕒 <b>Time:</b> <code>{timestamp}</code>"
        )
        
        await client.send_message(Config.LOG_CHANNEL, notification_text)
        logger.info(f"Force channel removed: {channel_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error sending force channel removed log: {e}")
        return False


async def send_admin_added_log(client: Client, new_admin_id: int, added_by_id: int) -> bool:
    """
    Send new admin added notification to LOG_GROUP_ID
    
    Args:
        client: Pyrogram Client instance
        new_admin_id: New admin user ID
        added_by_id: Admin user ID who added the new admin
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        if not Config.LOG_CHANNEL or Config.LOG_CHANNEL == 0:
            return False
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        notification_text = (
            f"👨‍💼 <b>New Admin Added</b>\n\n"
            f"👤 <b>New Admin ID:</b> <code>{new_admin_id}</code>\n"
            f"👤 <b>Added By:</b> <code>{added_by_id}</code>\n\n"
            f"🕒 <b>Time:</b> <code>{timestamp}</code>"
        )
        
        await client.send_message(Config.LOG_CHANNEL, notification_text)
        logger.info(f"New admin added: {new_admin_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error sending admin added log: {e}")
        return False


async def send_admin_removed_log(client: Client, removed_admin_id: int, removed_by_id: int) -> bool:
    """
    Send admin removed notification to LOG_GROUP_ID
    
    Args:
        client: Pyrogram Client instance
        removed_admin_id: Removed admin user ID
        removed_by_id: Admin user ID who removed the admin
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        if not Config.LOG_CHANNEL or Config.LOG_CHANNEL == 0:
            return False
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        notification_text = (
            f"❌ <b>Admin Removed</b>\n\n"
            f"👤 <b>Removed Admin ID:</b> <code>{removed_admin_id}</code>\n"
            f"👤 <b>Removed By:</b> <code>{removed_by_id}</code>\n\n"
            f"🕒 <b>Time:</b> <code>{timestamp}</code>"
        )
        
        await client.send_message(Config.LOG_CHANNEL, notification_text)
        logger.info(f"Admin removed: {removed_admin_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error sending admin removed log: {e}")
        return False
