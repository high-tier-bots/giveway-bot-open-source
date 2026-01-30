from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.enums import ChatMemberStatus
from config import Config
from database.mongo import db
from utils.logger import logger
from handlers.botlog import (
    send_admin_action_log,
    send_force_channel_added_log,
    send_force_channel_removed_log,
    send_admin_added_log,
    send_admin_removed_log,
    send_broadcast_log
)
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
    
    @app.on_message(filters.command("setbroadcast") & admin_only & filters.private)
    async def set_broadcast_target_command(client, message: Message):
        """Set broadcast target (users, channels, or both)"""
        try:
            if len(message.command) < 2:
                settings = db.settings.find_one({"_id": "main"})
                target = settings.get("broadcast_target", "both") if settings else "both"
                await message.reply_text(
                    f"ℹ️ **Current Broadcast Target:** {target}\n\n"
                    "**Usage:**\n"
                    "`/setbroadcast users` - Broadcast to users only\n"
                    "`/setbroadcast channels` - Broadcast to channels only\n"
                    "`/setbroadcast both` - Broadcast to users and channels"
                )
                return
            
            target = message.command[1].lower()
            
            if target not in ["users", "channels", "both"]:
                await message.reply_text("❌ Invalid target! Use: users, channels, or both")
                return
            
            db.settings.update_one(
                {"_id": "main"},
                {"$set": {"broadcast_target": target}},
                upsert=True
            )
            
            await message.reply_text(f"✅ Broadcast target set to: **{target}**")
            
            # Send log
            await send_admin_action_log(
                client,
                message.from_user.id,
                "Broadcast Target Updated",
                f"Target set to: {target}"
            )
            logger.info(f"Admin {message.from_user.id} set broadcast target to {target}")
            
        except Exception as e:
            logger.error(f"Error in set broadcast target: {e}")
            await message.reply_text("❌ Error updating broadcast target")
    
    @app.on_message(filters.command("broadcast") & admin_only)
    async def broadcast_command(client, message: Message):
        """Broadcast message to users/channels - select target with buttons"""
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
                broadcast_text = None
                message_id = broadcast_msg.id
            else:
                broadcast_text = message.text.split(None, 1)[1]
                broadcast_msg = None
                message_id = None
            
            # Select broadcast target
            buttons = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("👤 Users Only", callback_data="broadcast_select_users"),
                    InlineKeyboardButton("📺 Channels Only", callback_data="broadcast_select_channels")
                ],
                [
                    InlineKeyboardButton("👥 Both", callback_data="broadcast_select_both")
                ],
                [
                    InlineKeyboardButton("❌ Cancel", callback_data="broadcast_cancel")
                ]
            ])
            
            await message.reply_text(
                "📢 **Select Broadcast Target:**\n\n"
                "Choose where you want to send this message:",
                reply_markup=buttons
            )
            
            # Store broadcast data temporarily
            db.broadcasts.insert_one({
                "admin_id": message.from_user.id,
                "message_id": message_id,
                "text": broadcast_text,
                "status": "pending",
                "target": None,
                "created_at": datetime.now()
            })
            
        except Exception as e:
            logger.error(f"Error in broadcast: {e}")
            await message.reply_text("❌ Error preparing broadcast")
    
    @app.on_callback_query(filters.regex("^broadcast_select_"))
    async def handle_broadcast_target_selection(client, callback_query):
        """Handle broadcast target selection"""
        try:
            if not is_admin(callback_query.from_user.id):
                await callback_query.answer("❌ You are not authorized!", show_alert=True)
                return
            
            # Get the target from callback data
            target = callback_query.data.replace("broadcast_select_", "")
            
            # Find the pending broadcast
            broadcast = db.broadcasts.find_one({
                "admin_id": callback_query.from_user.id,
                "status": "pending"
            })
            
            if not broadcast:
                await callback_query.answer("❌ No pending broadcast found!", show_alert=True)
                return
            
            # Update broadcast with target
            db.broadcasts.update_one(
                {"_id": broadcast["_id"]},
                {"$set": {"target": target}}
            )
            
            # Get counts for display
            if target == "users":
                count = db.users.count_documents({})
                target_text = "👤 Users"
            elif target == "channels":
                count = db.chats.count_documents({})
                target_text = "📺 Channels"
            else:  # both
                count = db.users.count_documents({}) + db.chats.count_documents({})
                target_text = "👥 Users + Channels"
            
            # Show confirmation with selected target
            buttons = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("✅ Confirm", callback_data="broadcast_confirm"),
                    InlineKeyboardButton("❌ Cancel", callback_data="broadcast_cancel")
                ]
            ])
            
            await callback_query.message.edit_text(
                f"📢 **Broadcast Confirmation**\n\n"
                f"🎯 <b>Target:</b> {target_text}\n"
                f"👥 <b>Recipients:</b> {count:,}\n\n"
                f"Are you sure you want to send this broadcast?",
                reply_markup=buttons
            )
            
            await callback_query.answer("Target selected!", show_alert=False)
            logger.info(f"Admin {callback_query.from_user.id} selected broadcast target: {target}")
            
        except Exception as e:
            logger.error(f"Error in broadcast target selection: {e}")
            await callback_query.answer("❌ Error selecting target!", show_alert=True)
    
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
                try:
                    bot_member = await client.get_chat_member(chat.id, bot.id)
                    logger.info(f"Bot status in channel {chat.id}: {bot_member.status}")
                    
                    if bot_member.status not in [ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
                        await message.reply_text(
                            f"❌ Bot must be admin in the channel!\n"
                            f"Current status: {bot_member.status}\n\n"
                            f"Please make sure the bot has admin rights in **{chat.title}**"
                        )
                        return
                except Exception as member_error:
                    logger.error(f"Error checking bot membership: {member_error}")
                    await message.reply_text(
                        f"❌ Error checking bot status: {str(member_error)}\n\n"
                        f"Make sure:\n"
                        f"1. Bot is added to the channel\n"
                        f"2. Bot has admin privileges\n"
                        f"3. Channel username/ID is correct"
                    )
                    return
                
                # Add channel to database
                settings = db.settings.find_one({"_id": "main"})
                if settings is None:
                    db.settings.insert_one({"_id": "main", "force_channels": []})
                    settings = db.settings.find_one({"_id": "main"})
                
                force_channels = settings.get("force_channels", [])
                
                # Check if channel already exists
                channel_exists = False
                for fc in force_channels:
                    if isinstance(fc, dict) and fc.get("id") == chat.id:
                        channel_exists = True
                        break
                    elif isinstance(fc, int) and fc == chat.id:
                        channel_exists = True
                        break
                
                if channel_exists:
                    await message.reply_text(f"ℹ️ Channel **{chat.title}** is already in the list!")
                    return
                
                # Add channel as dictionary with id and username
                channel_data = {
                    "id": chat.id,
                    "username": f"@{chat.username}" if chat.username else None,
                    "title": chat.title
                }
                force_channels.append(channel_data)
                db.settings.update_one(
                    {"_id": "main"},
                    {"$set": {"force_channels": force_channels}},
                    upsert=True
                )
                
                await message.reply_text(
                    f"✅ Channel **{chat.title}** added successfully!\n"
                    f"Channel ID: `{chat.id}`"
                )
                
                # Send log
                await send_force_channel_added_log(
                    client,
                    chat.id,
                    chat.title,
                    message.from_user.id
                )
                logger.info(f"Admin {message.from_user.id} added channel {chat.id}")
                
            except Exception as e:
                logger.error(f"Error in add channel: {str(e)}")
                await message.reply_text(f"❌ Error: {str(e)}")
                
        except Exception as e:
            logger.error(f"Error in add channel: {e}")
            await message.reply_text("❌ Error adding channel")
    
    @app.on_message(filters.command("removechannel") & admin_only & filters.private)
    async def remove_channel_command(client, message: Message):
        """Remove force subscribe channel"""
        try:
            settings = db.settings.find_one({"_id": "main"})
            force_channels = settings.get("force_channels", []) if settings else []
            
            if not force_channels:
                await message.reply_text("ℹ️ No channels in the list!")
                return
            
            if len(message.command) < 2:
                # Show list of channels
                channel_list = "📋 **Force Subscribe Channels:**\n\n"
                for idx, channel in enumerate(force_channels, 1):
                    try:
                        if isinstance(channel, dict):
                            channel_id = channel.get("id")
                            channel_title = channel.get("title", "Unknown")
                            channel_list += f"{idx}. {channel_title} (`{channel_id}`)\n"
                        else:
                            # Old format (integer)
                            chat = await client.get_chat(channel)
                            channel_list += f"{idx}. {chat.title} (`{channel}`)\n"
                    except:
                        channel_id = channel.get("id") if isinstance(channel, dict) else channel
                        channel_list += f"{idx}. Unknown (`{channel_id}`)\n"
                
                first_channel_id = force_channels[0].get("id") if isinstance(force_channels[0], dict) else force_channels[0]
                channel_list += f"\n**Usage:** `/removechannel {first_channel_id}`"
                await message.reply_text(channel_list)
                return
            
            channel_id = int(message.command[1])
            
            # Check if channel exists in list
            channel_found = False
            updated_channels = []
            
            for channel in force_channels:
                if isinstance(channel, dict):
                    if channel.get("id") != channel_id:
                        updated_channels.append(channel)
                    else:
                        channel_found = True
                else:
                    # Old format (integer)
                    if channel != channel_id:
                        updated_channels.append(channel)
                    else:
                        channel_found = True
            
            if not channel_found:
                await message.reply_text("❌ Channel not in the list!")
                return
            
            db.settings.update_one(
                {"_id": "main"},
                {"$set": {"force_channels": updated_channels}}
            )
            
            await message.reply_text(f"✅ Channel removed successfully!")
            
            # Send log
            await send_force_channel_removed_log(
                client,
                channel_id,
                message.from_user.id
            )
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
            
            # Send log
            await send_admin_action_log(
                client,
                message.from_user.id,
                "Force Subscribe Updated",
                f"Force Subscribe {status}"
            )
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
            
            # Send log
            await send_admin_added_log(
                client,
                new_admin_id,
                message.from_user.id
            )
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
            
            # Send log
            await send_admin_removed_log(
                client,
                admin_to_remove,
                message.from_user.id
            )
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
            force_subscribe = settings.get("force_subscribe", False) if settings else False
            force_channels = settings.get("force_channels", []) if settings else []
            admins = settings.get("admins", Config.ADMINS) if settings else Config.ADMINS
            broadcast_target = settings.get("broadcast_target", "both") if settings else "both"
            
            settings_text = f"""⚙️ **Bot Settings**

🔔 **Force Subscribe:** {"✅ Enabled" if force_subscribe else "❌ Disabled"}
📺 **Force Channels:** {len(force_channels)}
👨‍💼 **Admins:** {len(admins)}
📝 **Log Channel:** `{Config.LOG_CHANNEL}`
📢 **Broadcast Target:** `{broadcast_target}`

**Commands:**
• `/setforce on/off` - Toggle force subscribe
• `/addchannel @channel` - Add channel
• `/removechannel <id>` - Remove channel
• `/addadmin <id>` - Add admin
• `/removeadmin <id>` - Remove admin
• `/setbroadcast users/channels/both` - Set broadcast target
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
    
    @app.on_callback_query(filters.regex("^broadcast_"))
    async def handle_broadcast_callback(client, callback_query):
        """Handle broadcast confirmation callbacks"""
        try:
            if not is_admin(callback_query.from_user.id):
                await callback_query.answer("❌ You are not authorized!", show_alert=True)
                return
            
            action = callback_query.data
            
            if action == "broadcast_cancel":
                # Delete pending broadcast
                db.broadcasts.delete_many({
                    "admin_id": callback_query.from_user.id,
                    "status": "pending"
                })
                await callback_query.message.edit_text("❌ Broadcast cancelled!")
                logger.info(f"Admin {callback_query.from_user.id} cancelled broadcast")
                return
            
            if action == "broadcast_confirm":
                # Get pending broadcast
                broadcast = db.broadcasts.find_one({
                    "admin_id": callback_query.from_user.id,
                    "status": "pending"
                })
                
                if not broadcast:
                    await callback_query.answer("❌ No pending broadcast found!", show_alert=True)
                    return
                
                await callback_query.message.edit_text("📢 Broadcasting... Please wait!")
                
                # Use the selected target from broadcast document
                broadcast_target = broadcast.get("target")
                if not broadcast_target:
                    await callback_query.answer("❌ Please select a target first!", show_alert=True)
                    return
                if broadcast_target not in ["users", "channels", "both"]:
                    broadcast_target = "both"
                
                # Get users to broadcast to
                if broadcast_target == "users":
                    recipients = db.users.find({})
                elif broadcast_target == "channels":
                    recipients = db.chats.find({})
                else:  # both
                    users = list(db.users.find({}))
                    chats = list(db.chats.find({}))
                    recipients = users + chats
                
                if broadcast_target == "users":
                    total_users = db.users.count_documents({})
                elif broadcast_target == "channels":
                    total_users = db.chats.count_documents({})
                else:  # both
                    total_users = db.users.count_documents({}) + db.chats.count_documents({})
                success = 0
                failed = 0
                blocked = 0
                
                # Broadcast to all recipients
                for recipient in recipients:
                    try:
                        if "user_id" in recipient:
                            recipient_id = recipient.get("user_id")
                        else:
                            recipient_id = recipient.get("chat_id")
                        
                        if broadcast.get("message_id"):
                            # Forward the message
                            await client.copy_message(
                                chat_id=recipient_id,
                                from_chat_id=callback_query.from_user.id,
                                message_id=broadcast["message_id"]
                            )
                        else:
                            # Send text message
                            await client.send_message(
                                chat_id=recipient_id,
                                text=broadcast["text"]
                            )
                        
                        success += 1
                        
                    except Exception as e:
                        error_str = str(e).lower()
                        if "blocked" in error_str or "user is deactivated" in error_str:
                            blocked += 1
                        else:
                            failed += 1
                        continue
                
                # Update broadcast status
                db.broadcasts.update_one(
                    {"_id": broadcast["_id"]},
                    {
                        "$set": {
                            "status": "completed",
                            "success": success,
                            "failed": failed,
                            "blocked": blocked,
                            "target": broadcast_target,
                            "completed_at": datetime.now()
                        }
                    }
                )
                
                result_text = f"""✅ **Broadcast Completed!**

📊 **Results:**
✅ Success: {success:,}
❌ Failed: {failed:,}
🚫 Blocked: {blocked:,}
👥 Total: {total_users:,}
🎯 Target: **{broadcast_target}**

📅 **Completed:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""
                await callback_query.message.edit_text(result_text)
                
                # Send log
                await send_broadcast_log(
                    client,
                    callback_query.from_user.id,
                    total_users,
                    success,
                    failed,
                    blocked
                )
                logger.info(f"Admin {callback_query.from_user.id} completed broadcast to {broadcast_target}: {success}/{total_users}")
                
        except Exception as e:
            logger.error(f"Error in broadcast callback: {e}")
            await callback_query.message.edit_text(f"❌ Error during broadcast: {str(e)}")
    
    logger.info("Admin handlers setup complete")
