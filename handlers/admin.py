from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from config import Config
from database.mongo import db
from utils.logger import logger
from datetime import datetime

def is_admin(user_id: int) -> bool:
    """Check if user is admin"""
    return user_id in Config.ADMINS

def admin_filter(_, __, message: Message):
    """Filter to check if user is admin"""
    return message.from_user and is_admin(message.from_user.id)

admin_only = filters.create(admin_filter)

def setup_admin_handlers(app: Client):
    """Setup admin command handlers"""
    
    @app.on_message(filters.command("stats") & admin_only & filters.private)
    async def admin_stats_command(client, message: Message):
        """Show bot statistics"""
        try:
            # Get statistics
            total_users = db.users.count_documents({})
            total_giveaways = db.giveaways.count_documents({})
            active_giveaways = db.giveaways.count_documents({"status": "active"})
            total_chats = db.chats.count_documents({})
            
            stats_text = f"""📊 **Bot Statistics**

👥 **Users:** {total_users:,}
🎁 **Total Giveaways:** {total_giveaways:,}
🔥 **Active Giveaways:** {active_giveaways:,}
💬 **Total Chats:** {total_chats:,}

📅 **Date:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""
            await message.reply_text(stats_text)
            logger.info(f"Admin {message.from_user.id} checked stats")
            
        except Exception as e:
            logger.error(f"Error in admin stats: {e}")
            await message.reply_text("❌ Error getting statistics")
    
    @app.on_message(filters.command("broadcast") & admin_only & filters.private)
    async def broadcast_command(client, message: Message):
        """Broadcast message to all users"""
        try:
            if len(message.command) < 2 and not message.reply_to_message:
                await message.reply_text(
                    "❌ **Usage:**\n"
                    "`/broadcast <message>` or reply to a message with `/broadcast`"
                )
                return
            
            # Get broadcast message
            if message.reply_to_message:
                broadcast_msg = message.reply_to_message
            else:
                broadcast_text = message.text.split(None, 1)[1]
                broadcast_msg = None
            
            # Confirm broadcast
            buttons = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("✅ Confirm", callback_data="broadcast_confirm"),
                    InlineKeyboardButton("❌ Cancel", callback_data="broadcast_cancel")
                ]
            ])
            
            users_count = db.users.count_documents({})
            await message.reply_text(
                f"📢 **Broadcast Confirmation**\n\n"
                f"👥 Users: {users_count:,}\n\n"
                f"Are you sure you want to send this broadcast?",
                reply_markup=buttons
            )
            
            # Store broadcast data temporarily
            db.broadcasts.insert_one({
                "admin_id": message.from_user.id,
                "message_id": message.reply_to_message.id if message.reply_to_message else None,
                "text": broadcast_text if not message.reply_to_message else None,
                "status": "pending",
                "created_at": datetime.now()
            })
            
        except Exception as e:
            logger.error(f"Error in broadcast: {e}")
            await message.reply_text("❌ Error preparing broadcast")
    
    @app.on_message(filters.command("addchannel") & admin_only & filters.private)
    async def add_channel_command(client, message: Message):
        """Add force subscribe channel"""
        try:
            if len(message.command) < 2:
                await message.reply_text(
                    "❌ **Usage:**\n"
                    "`/addchannel @channel_username` or `/addchannel -100123456789`"
                )
                return
            
            channel_input = message.command[1]
            
            # Try to get channel info
            try:
                if channel_input.startswith('@'):
                    chat = await client.get_chat(channel_input)
                else:
                    chat = await client.get_chat(int(channel_input))
                
                # Check if bot is admin in the channel
                bot = await client.get_me()
                bot_member = await client.get_chat_member(chat.id, bot.id)
                
                if bot_member.status not in ["administrator", "creator"]:
                    await message.reply_text("❌ Bot must be admin in the channel!")
                    return
                
                # Add channel to database
                settings = db.settings.find_one({"_id": "main"})
                force_channels = settings.get("force_channels", [])
                
                if chat.id in force_channels:
                    await message.reply_text(f"ℹ️ Channel **{chat.title}** is already in the list!")
                    return
                
                force_channels.append(chat.id)
                db.settings.update_one(
                    {"_id": "main"},
                    {"$set": {"force_channels": force_channels}}
                )
                
                await message.reply_text(
                    f"✅ Channel **{chat.title}** added successfully!\n"
                    f"Channel ID: `{chat.id}`"
                )
                logger.info(f"Admin {message.from_user.id} added channel {chat.id}")
                
            except Exception as e:
                await message.reply_text(f"❌ Error: {str(e)}\nMake sure the bot is admin in the channel!")
                
        except Exception as e:
            logger.error(f"Error in add channel: {e}")
            await message.reply_text("❌ Error adding channel")
    
    @app.on_message(filters.command("removechannel") & admin_only & filters.private)
    async def remove_channel_command(client, message: Message):
        """Remove force subscribe channel"""
        try:
            settings = db.settings.find_one({"_id": "main"})
            force_channels = settings.get("force_channels", [])
            
            if not force_channels:
                await message.reply_text("ℹ️ No channels in the list!")
                return
            
            if len(message.command) < 2:
                # Show list of channels
                channel_list = "📋 **Force Subscribe Channels:**\n\n"
                for idx, channel_id in enumerate(force_channels, 1):
                    try:
                        chat = await client.get_chat(channel_id)
                        channel_list += f"{idx}. {chat.title} (`{channel_id}`)\n"
                    except:
                        channel_list += f"{idx}. Unknown (`{channel_id}`)\n"
                
                channel_list += f"\n**Usage:** `/removechannel {force_channels[0]}`"
                await message.reply_text(channel_list)
                return
            
            channel_id = int(message.command[1])
            
            if channel_id not in force_channels:
                await message.reply_text("❌ Channel not in the list!")
                return
            
            force_channels.remove(channel_id)
            db.settings.update_one(
                {"_id": "main"},
                {"$set": {"force_channels": force_channels}}
            )
            
            await message.reply_text(f"✅ Channel removed successfully!")
            logger.info(f"Admin {message.from_user.id} removed channel {channel_id}")
            
        except Exception as e:
            logger.error(f"Error in remove channel: {e}")
            await message.reply_text("❌ Error removing channel")
    
    @app.on_message(filters.command("setforce") & admin_only & filters.private)
    async def set_force_command(client, message: Message):
        """Enable/disable force subscribe"""
        try:
            if len(message.command) < 2:
                settings = db.settings.find_one({"_id": "main"})
                status = "Enabled" if settings.get("force_subscribe", False) else "Disabled"
                await message.reply_text(
                    f"ℹ️ **Force Subscribe:** {status}\n\n"
                    "**Usage:**\n"
                    "`/setforce on` - Enable\n"
                    "`/setforce off` - Disable"
                )
                return
            
            action = message.command[1].lower()
            
            if action not in ["on", "off", "enable", "disable"]:
                await message.reply_text("❌ Invalid action! Use: on/off or enable/disable")
                return
            
            enable = action in ["on", "enable"]
            
            db.settings.update_one(
                {"_id": "main"},
                {"$set": {"force_subscribe": enable}}
            )
            
            status = "Enabled" if enable else "Disabled"
            await message.reply_text(f"✅ Force Subscribe {status} successfully!")
            logger.info(f"Admin {message.from_user.id} set force subscribe to {enable}")
            
        except Exception as e:
            logger.error(f"Error in set force: {e}")
            await message.reply_text("❌ Error updating settings")
    
    @app.on_message(filters.command("addadmin") & admin_only & filters.private)
    async def add_admin_command(client, message: Message):
        """Add new admin"""
        try:
            if len(message.command) < 2:
                await message.reply_text(
                    "❌ **Usage:**\n"
                    "`/addadmin <user_id>` or reply to user with `/addadmin`"
                )
                return
            
            if message.reply_to_message:
                new_admin_id = message.reply_to_message.from_user.id
            else:
                new_admin_id = int(message.command[1])
            
            settings = db.settings.find_one({"_id": "main"})
            admins = settings.get("admins", Config.ADMINS)
            
            if new_admin_id in admins:
                await message.reply_text("ℹ️ User is already an admin!")
                return
            
            admins.append(new_admin_id)
            db.settings.update_one(
                {"_id": "main"},
                {"$set": {"admins": admins}}
            )
            
            await message.reply_text(f"✅ Admin added successfully!\nUser ID: `{new_admin_id}`")
            logger.info(f"Admin {message.from_user.id} added new admin {new_admin_id}")
            
        except ValueError:
            await message.reply_text("❌ Invalid user ID!")
        except Exception as e:
            logger.error(f"Error in add admin: {e}")
            await message.reply_text("❌ Error adding admin")
    
    @app.on_message(filters.command("removeadmin") & admin_only & filters.private)
    async def remove_admin_command(client, message: Message):
        """Remove admin"""
        try:
            if len(message.command) < 2:
                settings = db.settings.find_one({"_id": "main"})
                admins = settings.get("admins", Config.ADMINS)
                
                admin_list = "👨‍💼 **Current Admins:**\n\n"
                for admin_id in admins:
                    admin_list += f"• `{admin_id}`\n"
                
                admin_list += f"\n**Usage:** `/removeadmin <user_id>`"
                await message.reply_text(admin_list)
                return
            
            admin_to_remove = int(message.command[1])
            
            settings = db.settings.find_one({"_id": "main"})
            admins = settings.get("admins", Config.ADMINS)
            
            if admin_to_remove not in admins:
                await message.reply_text("❌ User is not an admin!")
                return
            
            if admin_to_remove in Config.ADMINS:
                await message.reply_text("❌ Cannot remove permanent admin!")
                return
            
            admins.remove(admin_to_remove)
            db.settings.update_one(
                {"_id": "main"},
                {"$set": {"admins": admins}}
            )
            
            await message.reply_text(f"✅ Admin removed successfully!")
            logger.info(f"Admin {message.from_user.id} removed admin {admin_to_remove}")
            
        except ValueError:
            await message.reply_text("❌ Invalid user ID!")
        except Exception as e:
            logger.error(f"Error in remove admin: {e}")
            await message.reply_text("❌ Error removing admin")
    
    @app.on_message(filters.command("settings") & admin_only & filters.private)
    async def settings_command(client, message: Message):
        """Show bot settings"""
        try:
            settings = db.settings.find_one({"_id": "main"})
            force_subscribe = settings.get("force_subscribe", False)
            force_channels = settings.get("force_channels", [])
            admins = settings.get("admins", Config.ADMINS)
            
            settings_text = f"""⚙️ **Bot Settings**

🔔 **Force Subscribe:** {"✅ Enabled" if force_subscribe else "❌ Disabled"}
📺 **Force Channels:** {len(force_channels)}
👨‍💼 **Admins:** {len(admins)}
📝 **Log Channel:** `{Config.LOG_CHANNEL}`

**Commands:**
• `/setforce on/off` - Toggle force subscribe
• `/addchannel @channel` - Add channel
• `/removechannel <id>` - Remove channel
• `/addadmin <id>` - Add admin
• `/removeadmin <id>` - Remove admin
"""
            await message.reply_text(settings_text)
            
        except Exception as e:
            logger.error(f"Error in settings: {e}")
            await message.reply_text("❌ Error getting settings")
    
    @app.on_message(filters.command("admins") & admin_only & filters.private)
    async def admins_list_command(client, message: Message):
        """Show list of admins"""
        try:
            settings = db.settings.find_one({"_id": "main"})
            admins = settings.get("admins", Config.ADMINS)
            
            admin_text = "👨‍💼 **Bot Admins:**\n\n"
            
            for idx, admin_id in enumerate(admins, 1):
                try:
                    user = await client.get_users(admin_id)
                    name = user.first_name
                    username = f"@{user.username}" if user.username else "No username"
                    admin_text += f"{idx}. {name} ({username})\n   ID: `{admin_id}`\n\n"
                except:
                    admin_text += f"{idx}. Unknown User\n   ID: `{admin_id}`\n\n"
            
            await message.reply_text(admin_text)
            
        except Exception as e:
            logger.error(f"Error in admins list: {e}")
            await message.reply_text("❌ Error getting admins list")
    
    logger.info("Admin handlers setup complete")
