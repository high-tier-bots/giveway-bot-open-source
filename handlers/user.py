from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from config import Config
from database.mongo import db
from utils.logger import logger
from datetime import datetime

def setup_user_handlers(app: Client):
    """Setup user command handlers"""
    
    @app.on_message(filters.command("start") & filters.private)
    async def start_command(client, message: Message):
        """Handle /start command"""
        try:
            user_id = message.from_user.id
            
            # Save/update user in database
            user_data = {
                "user_id": user_id,
                "first_name": message.from_user.first_name,
                "username": message.from_user.username,
                "last_seen": datetime.now()
            }
            
            db.users.update_one(
                {"user_id": user_id},
                {"$set": user_data, "$setOnInsert": {"joined_at": datetime.now()}},
                upsert=True
            )
            
            # Check if user is admin
            is_admin = user_id in Config.ADMINS
            
            welcome_text = f"""👋 **Welcome {message.from_user.first_name}!**

🎁 Welcome to the Giveaway Bot!

I can help you participate in giveaways and win amazing prizes!

**Available Commands:**
• /join - Join active giveaway
• /stats - View your statistics
• /winners - View recent winners
• /help - Get help

{"**Admin Commands:**\n• /settings - Bot settings\n• /broadcast - Send broadcast\n• /addchannel - Add channel\n\nType /help for full admin commands list" if is_admin else ""}

Good luck! 🍀
"""
            
            buttons = InlineKeyboardMarkup([
                [InlineKeyboardButton("🎁 Join Giveaway", callback_data="join_giveaway")],
                [
                    InlineKeyboardButton("📊 Stats", callback_data="user_stats"),
                    InlineKeyboardButton("🏆 Winners", callback_data="winners_list")
                ],
                [InlineKeyboardButton("❓ Help", callback_data="help_menu")]
            ])
            
            await message.reply_text(welcome_text, reply_markup=buttons)
            logger.info(f"User {user_id} started the bot")
            
        except Exception as e:
            logger.error(f"Error in start command: {e}")
            await message.reply_text("❌ An error occurred. Please try again!")
    
    @app.on_message(filters.command("help") & filters.private)
    async def help_command(client, message: Message):
        """Handle /help command"""
        try:
            user_id = message.from_user.id
            is_admin = user_id in Config.ADMINS
            
            help_text = """📚 **Help Menu**

**User Commands:**
• `/start` - Start the bot
• `/join` - Join active giveaway
• `/stats` - View your statistics
• `/winners` - View recent winners
• `/help` - Show this help menu

**How to participate:**
1. Use /join to join active giveaway
2. Complete any required tasks
3. Wait for the giveaway to end
4. Winners will be announced automatically

**Need support?** Contact admins
"""
            
            if is_admin:
                help_text += """
**Admin Commands:**
• `/stats` - Bot statistics
• `/broadcast` - Send broadcast message
• `/addchannel` - Add force subscribe channel
• `/removechannel` - Remove force subscribe channel
• `/setforce` - Enable/disable force subscribe
• `/addadmin` - Add new admin
• `/removeadmin` - Remove admin
• `/admins` - List all admins
• `/settings` - View bot settings

**Giveaway Management:**
• `/creategiveaway` - Create new giveaway
• `/endgiveaway` - End active giveaway
• `/reroll` - Reroll winners
• `/participants` - View participants
"""
            
            await message.reply_text(help_text)
            
        except Exception as e:
            logger.error(f"Error in help command: {e}")
            await message.reply_text("❌ Error showing help menu")
    
    @app.on_message(filters.command("stats") & filters.private & ~filters.user(Config.ADMINS))
    async def user_stats_command(client, message: Message):
        """Show user statistics"""
        try:
            user_id = message.from_user.id
            
            # Get user data
            user = db.users.find_one({"user_id": user_id})
            
            if not user:
                await message.reply_text("❌ User data not found. Please use /start first")
                return
            
            # Count user's participations
            participations = db.giveaways.count_documents({"participants": user_id})
            wins = db.giveaways.count_documents({"winners": user_id})
            
            stats_text = f"""📊 **Your Statistics**

👤 **Name:** {message.from_user.first_name}
🆔 **User ID:** `{user_id}`
📅 **Joined:** {user.get('joined_at', 'Unknown').strftime('%Y-%m-%d') if isinstance(user.get('joined_at'), datetime) else 'Unknown'}

🎁 **Giveaways Joined:** {participations}
🏆 **Wins:** {wins}
📈 **Win Rate:** {(wins/participations*100) if participations > 0 else 0:.1f}%

Keep participating to win more prizes! 🍀
"""
            
            await message.reply_text(stats_text)
            
        except Exception as e:
            logger.error(f"Error in user stats: {e}")
            await message.reply_text("❌ Error getting statistics")
    
    @app.on_message(filters.command("winners") & filters.private)
    async def winners_command(client, message: Message):
        """Show recent winners"""
        try:
            # Get recent completed giveaways
            recent_giveaways = list(db.giveaways.find(
                {"status": "completed", "winners": {"$exists": True, "$ne": []}}
            ).sort("end_date", -1).limit(5))
            
            if not recent_giveaways:
                await message.reply_text("ℹ️ No winners yet!")
                return
            
            winners_text = "🏆 **Recent Winners**\n\n"
            
            for idx, giveaway in enumerate(recent_giveaways, 1):
                title = giveaway.get("title", "Unknown")
                winners = giveaway.get("winners", [])
                
                winners_text += f"{idx}. **{title}**\n"
                
                for winner_id in winners[:3]:  # Show max 3 winners per giveaway
                    try:
                        user = await client.get_users(winner_id)
                        name = user.first_name
                        username = f"@{user.username}" if user.username else ""
                        winners_text += f"   🎉 {name} {username}\n"
                    except:
                        winners_text += f"   🎉 User {winner_id}\n"
                
                winners_text += "\n"
            
            await message.reply_text(winners_text)
            
        except Exception as e:
            logger.error(f"Error in winners command: {e}")
            await message.reply_text("❌ Error getting winners list")
    
    logger.info("User handlers setup complete")
