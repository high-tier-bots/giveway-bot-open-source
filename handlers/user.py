from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery
from database.models import User, Giveaway, Settings, Chat
from handlers.forcesubscribe import ForceSubscribeService
from handlers.referral import ReferralService
from utils.reply import main_menu_keyboard
from utils.helpers import get_user_mention, format_time_remaining, format_datetime
from utils.logger import logger
from handlers.botlog import send_bot_start_log, send_user_joined_giveaway_log

def setup_user_handlers(app: Client):
    force_subscribe_service = ForceSubscribeService(app)
    
    @app.on_message(filters.command("start") & filters.private)
    async def start_command(client: Client, message: Message):
        user_id = message.from_user.id
        username = message.from_user.username
        
        # Extract referrer ID
        referrer_id = None
        if len(message.command) > 1:
            referrer_id = ReferralService.extract_referrer_id(message.command[1])
        
        # Add user to database
        is_new = User.add_user(user_id, username, referrer_id)
        
        # Check if user is admin
        admins = Settings.get_admins()
        is_admin = user_id in admins
        
        if is_new:
            # await notification_service.notify_new_user(user_id, username)
            # Send log for new user
            await send_bot_start_log(client, message.from_user)
            logger.info(f"New user started bot: {user_id}")
        
        welcome_text = f"👋 **Welcome {message.from_user.first_name}!**\n\n"
        welcome_text += "🎁 I'm a Giveaway Bot. You can participate in giveaways and win amazing prizes!\n\n"
        welcome_text += "**Available Commands:**\n"
        welcome_text += "• /join - Join active giveaway\n"
        welcome_text += "• /stats - View your statistics\n"
        welcome_text += "• /refer - Get your referral link\n"
        welcome_text += "• /winners - View recent winners\n"
        welcome_text += "• /help - Get help\n\n"
        
        if is_admin:
            welcome_text += "👮 **You are an admin!**\n"
            welcome_text += "Use /help for admin commands."
        
        await message.reply_text(
            welcome_text,
            reply_markup=main_menu_keyboard(is_admin)
        )
    
    @app.on_message(filters.command("join") & filters.private)
    async def join_command(client: Client, message: Message):
        user_id = message.from_user.id
        
        # Check if user exists
        if not User.get_user(user_id):
            await message.reply_text("Please /start the bot first!")
            return
        
        # Get active giveaway
        giveaway = Giveaway.get_active_giveaway()
        if not giveaway:
            await message.reply_text("❌ No active giveaway at the moment!")
            return
        
        # Check force subscribe
        is_subscribed, not_subscribed = await force_subscribe_service.check_user_subscribed(user_id)
        if not is_subscribed:
            await force_subscribe_service.send_force_subscribe_message(message, not_subscribed)
            return
        
        # Check if already participated
        if user_id in giveaway.get("participants", []):
            await message.reply_text("✅ You have already joined this giveaway!")
            return
        
        # Add participant
        Giveaway.add_participant(giveaway["giveaway_id"], user_id)
        
        participants_count = Giveaway.get_participants_count(giveaway["giveaway_id"])
        time_remaining = format_time_remaining(giveaway["end_time"])
        
        success_text = f"🎉 **Successfully joined the giveaway!**\n\n"
        success_text += f"🎁 **Prize:** {giveaway['prize']}\n"
        success_text += f"👥 **Total Participants:** {participants_count}\n"
        success_text += f"⏰ **Time Remaining:** {time_remaining}\n\n"
        success_text += "🤞 Good luck!"
        
        await message.reply_text(success_text)
        
        # Send log for giveaway join
        await send_user_joined_giveaway_log(
            client,
            user_id,
            message.from_user.username,
            giveaway["giveaway_id"]
        )
        logger.info(f"User {user_id} joined giveaway {giveaway['giveaway_id']}")
    
    @app.on_message(filters.command("stats") & filters.private)
    async def stats_command(client: Client, message: Message):
        user_id = message.from_user.id
        user = User.get_user(user_id)
        
        if not user:
            await message.reply_text("Please /start the bot first!")
            return
        
        referral_stats = ReferralService.get_referral_stats(user_id)
        
        stats_text = f"📊 **Your Statistics**\n\n"
        stats_text += f"👤 **User ID:** `{user_id}`\n"
        stats_text += f"📅 **Joined:** {format_datetime(user['joined_at'])}\n"
        stats_text += f"👥 **Referrals:** {referral_stats['total_referrals']}\n"
        
        await message.reply_text(stats_text)
    
    @app.on_message(filters.command("refer") & filters.private)
    async def refer_command(client: Client, message: Message):
        user_id = message.from_user.id
        bot_username = (await client.get_me()).username
        
        referral_link = ReferralService.get_referral_link(bot_username, user_id)
        referral_stats = ReferralService.get_referral_stats(user_id)
        
        refer_text = f"👥 **Your Referral Link**\n\n"
        refer_text += f"🔗 `{referral_link}`\n\n"
        refer_text += f"📊 **Total Referrals:** {referral_stats['total_referrals']}\n\n"
        refer_text += "Share this link with your friends to earn rewards!"
        
        await message.reply_text(refer_text)
    
    @app.on_message(filters.command("winners") & filters.private)
    async def winners_command(client: Client, message: Message):
        # Get recent ended giveaways with winners
        ended_giveaways = list(app.db.giveaways.find({"status": "ended"}).sort("created_at", -1).limit(5))
        
        if not ended_giveaways:
            await message.reply_text("❌ No winners yet!")
            return
        
        winners_text = "🏆 **Recent Winners**\n\n"
        
        for giveaway in ended_giveaways:
            winners = giveaway.get("winners", [])
            if winners:
                winners_text += f"🎁 **{giveaway['prize']}**\n"
                for winner_id in winners[:3]:  # Show max 3 winners
                    try:
                        user = await client.get_users(winner_id)
                        winners_text += f"   👤 {get_user_mention(user)}\n"
                    except:
                        winners_text += f"   👤 User {winner_id}\n"
                winners_text += "\n"
        
        await message.reply_text(winners_text, disable_web_page_preview=True)
    
    @app.on_message(filters.command("help") & filters.private)
    async def help_command(client: Client, message: Message):
        user_id = message.from_user.id
        admins = Settings.get_admins()
        is_admin = user_id in admins
        
        help_text = "❓ **Help & Commands**\n\n"
        help_text += "**User Commands:**\n"
        help_text += "• /start - Start the bot\n"
        help_text += "• /join - Join active giveaway\n"
        help_text += "• /stats - View your statistics\n"
        help_text += "• /refer - Get referral link\n"
        help_text += "• /winners - View recent winners\n"
        help_text += "• /help - Show this help message\n\n"
        
        if is_admin:
            help_text += "**Admin Commands:**\n"
            help_text += "• /creategiveaway - Create new giveaway\n"
            help_text += "• /endgiveaway - End active giveaway\n"
            help_text += "• /reroll - Reroll winners\n"
            help_text += "• /broadcast - Send broadcast message\n"
            help_text += "• /addchannel - Add force subscribe channel\n"
            help_text += "• /removechannel - Remove force subscribe channel\n"
            help_text += "• /setforce - Enable/disable force subscribe\n"
            help_text += "• /loggroup - Set log group\n"
            help_text += "• /participants - View participants\n"
            help_text += "• /addadmin - Add new admin\n"
            help_text += "• /removeadmin - Remove admin\n"
            help_text += "• /settings - Bot settings\n"
        
        await message.reply_text(help_text)
    
    @app.on_callback_query(filters.regex("^join_giveaway$"))
    async def join_giveaway_callback(client: Client, callback_query: CallbackQuery):
        user_id = callback_query.from_user.id
        
        # Check force subscribe
        is_subscribed, not_subscribed = await force_subscribe_service.check_user_subscribed(user_id)
        if not is_subscribed:
            await callback_query.answer("⚠️ You must join all channels first!", show_alert=True)
            return
        
        giveaway = Giveaway.get_active_giveaway()
        if not giveaway:
            await callback_query.answer("❌ Giveaway has ended!", show_alert=True)
            return
        
        if user_id in giveaway.get("participants", []):
            await callback_query.answer("✅ Already joined!", show_alert=True)
            return
        
        Giveaway.add_participant(giveaway["giveaway_id"], user_id)
        await callback_query.answer("🎉 Successfully joined the giveaway!", show_alert=True)
    
    @app.on_callback_query(filters.regex("^check_subscription$"))
    async def check_subscription_callback(client: Client, callback_query: CallbackQuery):
        user_id = callback_query.from_user.id
        
        is_subscribed, not_subscribed = await force_subscribe_service.check_user_subscribed(user_id)
        if is_subscribed:
            await callback_query.answer("✅ Subscription verified! Now you can join the giveaway.", show_alert=True)
            await callback_query.message.delete()
        else:
            await callback_query.answer("⚠️ You haven't joined all channels yet!", show_alert=True)
    
    @app.on_callback_query(filters.regex("^close$"))
    async def close_callback(client: Client, callback_query: CallbackQuery):
        await callback_query.message.delete()
    
    # Handle bot added to group/channel
    @app.on_message(filters.new_chat_members)
    async def bot_added_to_chat(client: Client, message: Message):
        for member in message.new_chat_members:
            if member.id == (await client.get_me()).id:
                chat_id = message.chat.id
                chat_title = message.chat.title
                chat_type = message.chat.type.value if hasattr(message.chat.type, 'value') else str(message.chat.type)
                
                # Add chat to database
                Chat.add_chat(chat_id, message.chat.type, message.from_user.id)
                
                # Notify
                # await notification_service.notify_bot_added_to_chat(chat_id, chat_title, chat_type)
                logger.info(f"Bot added to {chat_type}: {chat_id}")
    
    # Store reference to db in app for easy access
    app.db = app.db if hasattr(app, 'db') else None
    from database.mongo import db as mongodb
    app.db = mongodb.db
