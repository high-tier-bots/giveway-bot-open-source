import asyncio
import os
from pyrogram import Client, idle
from pyrogram.enums import ParseMode
from database.mongo import db
from handlers.user import setup_user_handlers
from handlers.admin import setup_admin_handlers
from handlers.giveaway import setup_giveaway_handlers
# from handlers.broadcast import setup_broadcast_handlers
# from services.notification import NotificationService
from config import Config
from utils.logger import logger
from pyrogram.types import BotCommand, BotCommandScopeChat, BotCommandScopeDefault
                

class GiveawayBot:
    def __init__(self):
        self.app = Client(
            "giveaway_bot",
            api_id=Config.API_ID,
            api_hash=Config.API_HASH,
            bot_token=Config.BOT_TOKEN,
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Setup handlers
        setup_user_handlers(self.app)
        setup_admin_handlers(self.app)
        setup_giveaway_handlers(self.app)
        # setup_broadcast_handlers(self.app)
        # self.setup_system_handlers()
        
        logger.info("Bot initialized successfully")
    
    # def setup_system_handlers(self):
    #     """Setup system-level handlers like chat member updates"""
    #     notification_service = NotificationService(self.app)
        
    #     @self.app.on_chat_member_updated()
    #     async def on_chat_member_updated(client, chat_member_updated):
    #         """Handle when bot is added to or removed from a group/channel"""
    #         # Check if it's about the bot itself
    #         if chat_member_updated.new_chat_member.user.id == (await client.get_me()).id:
    #             chat = chat_member_updated.chat
    #             old_status = chat_member_updated.old_chat_member.status if chat_member_updated.old_chat_member else None
    #             new_status = chat_member_updated.new_chat_member.status
                
    #             # Bot was added to group/channel
    #             if old_status in [None, "left", "kicked"] and new_status in ["member", "administrator"]:
    #                 await notification_service.notify_bot_added_to_chat(
    #                     chat.id,
    #                     chat.title,
    #                     chat.type.value
    #                 )
    #                 logger.info(f"Bot added to {chat.type.value}: {chat.title} ({chat.id})")
    
    async def start(self):
        """Start the bot"""
        await self.app.start()
        
        bot_info = await self.app.get_me()
        logger.info(f"Bot started: @{bot_info.username}")
        
        # Set bot commands
        await self.set_commands()
        
        print(f"[OK] Bot is running as @{bot_info.username}")
        print(f"[INFO] MongoDB: Connected")
        print(f"[INFO] Admins: {len(Config.ADMINS)}")
        print("\n[OK] Bot is ready to receive messages!\n")
        print("[INFO] Press Ctrl+C to stop the bot\n")
        
        # Keep the bot running
        await idle()
    
    async def set_commands(self):
        """Set bot commands menu"""
    
        user_commands = [
            BotCommand("start", "Start the bot"),
            BotCommand("join", "Join active giveaway"),
            BotCommand("stats", "View your statistics"),
            BotCommand("refer", "Get referral link"),
            BotCommand("winners", "View recent winners"),
            BotCommand("help", "Get help")
        ]
        
        admin_commands = [
            BotCommand("start", "Start the bot"),
            BotCommand("join", "Join active giveaway"),
            BotCommand("stats", "View your statistics"),
            BotCommand("refer", "Get referral link"),
            BotCommand("winners", "View recent winners"),
            BotCommand("help", "Get help"),
            BotCommand("creategiveaway", "Create new giveaway"),
            BotCommand("endgiveaway", "End active giveaway"),
            BotCommand("reroll", "Reroll winners"),
            BotCommand("sendgiveaway", "Send giveaway to specific chat"),
            BotCommand("broadcast", "Send broadcast message"),
            BotCommand("addchannel", "Add force subscribe channel"),
            BotCommand("removechannel", "Remove force subscribe channel"),
            BotCommand("setforce", "Enable/disable force subscribe"),
            BotCommand("loggroup", "Set log group"),
            BotCommand("participants", "View participants"),
            BotCommand("addadmin", "Add new admin"),
            BotCommand("removeadmin", "Remove admin"),
            BotCommand("settings", "Bot settings"),
            BotCommand("admins", "View admin list")
        ]
        
        # Set default commands for all users
        await self.app.set_bot_commands(user_commands, scope=BotCommandScopeDefault())
        
        # Set admin commands for each admin user
        for admin_id in Config.ADMINS:
            try:
                await self.app.set_bot_commands(admin_commands, scope=BotCommandScopeChat(admin_id))
            except Exception as e:
                logger.warning(f"Could not set commands for admin {admin_id}: {e}")
        
        logger.info("Bot commands set successfully")
    
    async def stop(self):
        """Stop the bot"""
        await self.app.stop()
        db.close()
        logger.info("Bot stopped")

async def main():
    bot = GiveawayBot()
    
    try:
        await bot.start()
    except (KeyboardInterrupt, SystemExit):
        print("\n[WARNING] Bot stopped by user")
    except Exception as e:
        logger.error(f"Error running bot: {e}")
    finally:
        try:
            await bot.stop()
        except:
            pass

if __name__ == "__main__":
    asyncio.run(main())
