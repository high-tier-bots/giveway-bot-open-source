from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery
from datetime import datetime, timedelta
from database.models import Giveaway, Settings
from utils.inline import join_giveaway_keyboard, force_subscribe_keyboard
from utils.helpers import generate_giveaway_id, select_random_winners, format_time_remaining, get_user_mention
from utils.logger import logger

def is_admin_filter(func):
    """Decorator to check if user is admin"""
    async def wrapper(client: Client, message: Message):
        user_id = message.from_user.id
        admins = Settings.get_admins()
        
        if user_id not in admins:
            await message.reply_text("❌ This command is only for admins!")
            return
        
        return await func(client, message)
    return wrapper

def setup_giveaway_handlers(app: Client):
    # notification_service = NotificationService(app)
    
    # Store conversation states
    app.giveaway_states = {}
    
    @app.on_message(filters.command("creategiveaway") & filters.private)
    @is_admin_filter
    async def create_giveaway_command(client: Client, message: Message):
        # Check if there's already an active giveaway
        active_giveaway = Giveaway.get_active_giveaway()
        if active_giveaway:
            await message.reply_text("❌ There's already an active giveaway! End it first.")
            return
        
        app.giveaway_states[message.from_user.id] = {"step": "prize"}
        await message.reply_text(
            "🎁 **Create New Giveaway**\n\n"
            "Please enter the prize name:"
        )
    
    @app.on_message(filters.text & filters.private)
    async def handle_giveaway_creation(client: Client, message: Message):
        user_id = message.from_user.id
        
        if user_id not in app.giveaway_states:
            return
        
        state = app.giveaway_states[user_id]
        
        if state["step"] == "prize":
            state["prize"] = message.text
            state["step"] = "description"
            await message.reply_text("📝 Now enter the giveaway description:")
        
        elif state["step"] == "description":
            state["description"] = message.text
            state["step"] = "duration"
            await message.reply_text(
                "⏰ Enter the giveaway duration:\n\n"
                "Examples: 1h, 30m, 2d, 1h30m\n"
                "(h=hours, m=minutes, d=days)"
            )
        
        elif state["step"] == "duration":
            try:
                # Parse duration
                duration_text = message.text.lower()
                total_seconds = 0
                
                # Parse days, hours, minutes
                if 'd' in duration_text:
                    days = int(duration_text.split('d')[0])
                    total_seconds += days * 86400
                    duration_text = duration_text.split('d')[1] if len(duration_text.split('d')) > 1 else ""
                
                if 'h' in duration_text:
                    hours = int(duration_text.split('h')[0])
                    total_seconds += hours * 3600
                    duration_text = duration_text.split('h')[1] if len(duration_text.split('h')) > 1 else ""
                
                if 'm' in duration_text:
                    minutes = int(duration_text.split('m')[0])
                    total_seconds += minutes * 60
                
                if total_seconds == 0:
                    raise ValueError("Invalid duration")
                
                end_time = datetime.now() + timedelta(seconds=total_seconds)
                state["end_time"] = end_time
                state["step"] = "winners"
                
                await message.reply_text("🏆 Enter the number of winners:")
            
            except Exception as e:
                await message.reply_text("❌ Invalid duration format! Try again (e.g., 1h, 30m, 2d)")
        
        elif state["step"] == "winners":
            try:
                winners_count = int(message.text)
                if winners_count < 1:
                    raise ValueError("Winners count must be at least 1")
                
                # Create giveaway
                giveaway_id = generate_giveaway_id()
                giveaway = Giveaway.create_giveaway(
                    giveaway_id=giveaway_id,
                    prize=state["prize"],
                    description=state["description"],
                    end_time=state["end_time"],
                    winners_count=winners_count,
                    created_by=user_id
                )
                
                # Clear state
                del app.giveaway_states[user_id]
                
                # Send notification
                # await notification_service.notify_giveaway_started(
                #     giveaway_id,
                #     state["prize"],
                #     state["end_time"].strftime("%Y-%m-%d %H:%M:%S")
                # )
                
                # Confirm to admin
                confirm_text = f"✅ **Giveaway Created!**\n\n"
                confirm_text += f"🆔 **ID:** `{giveaway_id}`\n"
                confirm_text += f"🎁 **Prize:** {state['prize']}\n"
                confirm_text += f"📝 **Description:** {state['description']}\n"
                confirm_text += f"⏰ **Ends:** {state['end_time'].strftime('%Y-%m-%d %H:%M:%S')}\n"
                confirm_text += f"🏆 **Winners:** {winners_count}\n\n"
                confirm_text += "📢 Broadcasting to users and groups..."
                
                await message.reply_text(confirm_text)
                
                # Broadcast giveaway announcement
                success, failed = await broadcast_giveaway_announcement(client, giveaway)
                
                # Send broadcast stats
                await message.reply_text(
                    f"✅ **Broadcast Complete!**\n\n"
                    f"✅ Success: {success}\n"
                    f"❌ Failed: {failed}"
                )
                
                logger.info(f"Giveaway {giveaway_id} created by {user_id}")
            
            except ValueError:
                await message.reply_text("❌ Invalid number! Please enter a valid number of winners:")
    
    async def broadcast_giveaway_announcement(client: Client, giveaway):
        """Broadcast new giveaway to all users, groups, and channels"""
        from database.models import User, Chat
        
        announcement = f"🎉 **NEW GIVEAWAY!**\n\n"
        announcement += f"🎁 **Prize:** {giveaway['prize']}\n"
        announcement += f"📝 **Description:** {giveaway['description']}\n"
        announcement += f"⏰ **Ends:** {format_time_remaining(giveaway['end_time'])}\n"
        announcement += f"🏆 **Winners:** {giveaway['winners_count']}\n\n"
        announcement += "Click below to join!"
        
        keyboard = join_giveaway_keyboard()
        success = 0
        failed = 0
        
        # Send to all users
        users = User.get_all_users()
        for user in users:
            try:
                await client.send_message(
                    user["user_id"],
                    announcement,
                    reply_markup=keyboard
                )
                success += 1
            except Exception as e:
                failed += 1
                logger.error(f"Failed to send giveaway announcement to user {user['user_id']}: {e}")
        
        # Send to all groups and channels
        chats = Chat.get_all_chats()
        for chat in chats:
            try:
                await client.send_message(
                    chat["chat_id"],
                    announcement,
                    reply_markup=keyboard
                )
                success += 1
            except Exception as e:
                failed += 1
                logger.error(f"Failed to send giveaway announcement to chat {chat['chat_id']}: {e}")
        
        logger.info(f"Giveaway announcement sent: {success} success, {failed} failed")
        return success, failed
    
    @app.on_message(filters.command("endgiveaway") & filters.private)
    @is_admin_filter
    async def end_giveaway_command(client: Client, message: Message):
        giveaway = Giveaway.get_active_giveaway()
        if not giveaway:
            await message.reply_text("❌ No active giveaway to end!")
            return
        
        await end_giveaway(client, giveaway, message.from_user.id)
        await message.reply_text("✅ Giveaway ended successfully!")
    
    async def end_giveaway(client: Client, giveaway, ended_by=None):
        """End a giveaway and select winners"""
        giveaway_id = giveaway["giveaway_id"]
        participants = giveaway.get("participants", [])
        winners_count = giveaway["winners_count"]
        
        if len(participants) == 0:
            # No participants
            Giveaway.end_giveaway(giveaway_id)
            result_text = f"🏁 **Giveaway Ended**\n\n"
            result_text += f"🎁 **Prize:** {giveaway['prize']}\n"
            result_text += f"❌ **No participants!**"
            
            # Notify users
            from database.models import User
            users = User.get_all_users()
            for user in users:
                try:
                    await client.send_message(user["user_id"], result_text)
                except:
                    pass
            
            return
        
        # Select winners
        winners = select_random_winners(participants, winners_count)
        Giveaway.end_giveaway(giveaway_id, winners)
        
        # Send notifications
        # await notification_service.notify_giveaway_ended(
        #     giveaway_id,
        #     giveaway["prize"],
        #     len(participants),
        #     len(winners)
        # )
        # await notification_service.notify_winner_selected(giveaway_id, winners)
        
        # Prepare winner announcement
        result_text = f"🏁 **Giveaway Ended!**\n\n"
        result_text += f"🎁 **Prize:** {giveaway['prize']}\n"
        result_text += f"👥 **Participants:** {len(participants)}\n\n"
        result_text += f"🎉 **Winners:**\n"
        
        for winner_id in winners:
            try:
                winner_user = await client.get_users(winner_id)
                result_text += f"  🏆 {get_user_mention(winner_user)}\n"
            except:
                result_text += f"  🏆 User {winner_id}\n"
        
        result_text += f"\n🎊 Congratulations to all winners!"
        
        # Notify all participants
        for participant_id in participants:
            try:
                await client.send_message(participant_id, result_text, disable_web_page_preview=True)
            except Exception as e:
                logger.error(f"Failed to notify participant {participant_id}: {e}")
        
        logger.info(f"Giveaway {giveaway_id} ended with {len(winners)} winners")
    
    @app.on_message(filters.command("reroll") & filters.private)
    @is_admin_filter
    async def reroll_command(client: Client, message: Message):
        # Get last ended giveaway
        last_giveaway = app.db.giveaways.find_one(
            {"status": "ended"},
            sort=[("created_at", -1)]
        )
        
        if not last_giveaway:
            await message.reply_text("❌ No ended giveaway found!")
            return
        
        participants = last_giveaway.get("participants", [])
        if not participants:
            await message.reply_text("❌ No participants in the giveaway!")
            return
        
        # Select new winners
        winners_count = last_giveaway["winners_count"]
        new_winners = select_random_winners(participants, winners_count)
        
        # Update winners
        app.db.giveaways.update_one(
            {"giveaway_id": last_giveaway["giveaway_id"]},
            {"$set": {"winners": new_winners}}
        )
        
        # Notify
        # await notification_service.notify_winner_selected(last_giveaway["giveaway_id"], new_winners)
        
        # Prepare announcement
        result_text = f"🔄 **Winners Rerolled!**\n\n"
        result_text += f"🎁 **Prize:** {last_giveaway['prize']}\n\n"
        result_text += f"🎉 **New Winners:**\n"
        
        for winner_id in new_winners:
            try:
                winner_user = await client.get_users(winner_id)
                result_text += f"  🏆 {get_user_mention(winner_user)}\n"
            except:
                result_text += f"  🏆 User {winner_id}\n"
        
        await message.reply_text(result_text, disable_web_page_preview=True)
        
        # Notify participants
        for participant_id in participants:
            try:
                await client.send_message(participant_id, result_text, disable_web_page_preview=True)
            except:
                pass
        
        logger.info(f"Giveaway {last_giveaway['giveaway_id']} rerolled")
    
    @app.on_message(filters.regex("^🎁 Active Giveaway$") & filters.private)
    async def active_giveaway_button(client: Client, message: Message):
        giveaway = Giveaway.get_active_giveaway()
        
        if not giveaway:
            await message.reply_text("❌ No active giveaway at the moment!")
            return
        
        participants_count = len(giveaway.get("participants", []))
        time_remaining = format_time_remaining(giveaway["end_time"])
        
        info_text = f"🎁 **Active Giveaway**\n\n"
        info_text += f"🎁 **Prize:** {giveaway['prize']}\n"
        info_text += f"📝 **Description:** {giveaway['description']}\n"
        info_text += f"👥 **Participants:** {participants_count}\n"
        info_text += f"🏆 **Winners:** {giveaway['winners_count']}\n"
        info_text += f"⏰ **Time Remaining:** {time_remaining}\n\n"
        info_text += "Use /join to participate!"
        
        await message.reply_text(info_text, reply_markup=join_giveaway_keyboard())
    
    @app.on_callback_query(filters.regex("^join_giveaway$"))
    async def join_giveaway_callback(client: Client, callback_query: CallbackQuery):
        """Handle join giveaway button clicks from group/channel/private"""
        user_id = callback_query.from_user.id
        
        # Get active giveaway
        giveaway = Giveaway.get_active_giveaway()
        if not giveaway:
            await callback_query.answer("❌ No active giveaway at the moment!", show_alert=True)
            return
        
        # Check force subscribe
        from handlers.forcesubscribe import ForceSubscribeService
        force_subscribe_service = ForceSubscribeService(client)
        is_subscribed, not_subscribed = await force_subscribe_service.check_user_subscribed(user_id)
        
        if not is_subscribed:
            # User not subscribed to required channels
            text = "⚠️ **You must join the following channels to participate:**\n\n"
            text += "Please join all channels and click '✅ Try Again'"
            
            keyboard = force_subscribe_keyboard(not_subscribed)
            await callback_query.answer("Please join required channels first!", show_alert=True)
            
            # Try to send message in private chat (may fail if user never started bot)
            try:
                await client.send_message(user_id, text, reply_markup=keyboard)
            except:
                # Can't send private message, just show alert
                await callback_query.answer(
                    "⚠️ Please join the required channels and start the bot in private chat!",
                    show_alert=True
                )
            return
        
        # Check if already participated
        if user_id in giveaway.get("participants", []):
            await callback_query.answer("✅ You have already joined this giveaway!", show_alert=True)
            return
        
        # Add participant
        Giveaway.add_participant(giveaway["giveaway_id"], user_id)
        
        # Add user to database if not exists
        from database.models import User
        User.add_user(user_id, callback_query.from_user.username)
        
        participants_count = Giveaway.get_participants_count(giveaway["giveaway_id"])
        
        # # Notify log group
        # await notification_service.notify_giveaway_participation(
        #     user_id,
        #     callback_query.from_user.username,
        #     giveaway["giveaway_id"],
        #     giveaway["prize"]
        # )
        
        # Show success message
        success_msg = f"🎉 Successfully joined!\n\n"
        success_msg += f"🎁 Prize: {giveaway['prize']}\n"
        success_msg += f"👥 Participants: {participants_count}"
        
        await callback_query.answer(success_msg, show_alert=True)
        
        logger.info(f"User {user_id} joined giveaway {giveaway['giveaway_id']} via callback")
    
    @app.on_callback_query(filters.regex("^check_subscription$"))
    async def check_subscription_callback(client: Client, callback_query: CallbackQuery):
        """Handle Try Again button for force subscribe check"""
        user_id = callback_query.from_user.id
        
        # Get active giveaway
        giveaway = Giveaway.get_active_giveaway()
        if not giveaway:
            await callback_query.answer("❌ No active giveaway at the moment!", show_alert=True)
            return
        
        # Check force subscribe again
        from handlers.forcesubscribe import ForceSubscribeService
        force_subscribe_service = ForceSubscribeService(client)
        is_subscribed, not_subscribed = await force_subscribe_service.check_user_subscribed(user_id)
        
        if not is_subscribed:
            # Still not subscribed
            await callback_query.answer("❌ Please join all required channels first!", show_alert=True)
            return
        
        # Check if already participated
        if user_id in giveaway.get("participants", []):
            await callback_query.answer("✅ You have already joined this giveaway!", show_alert=True)
            # Delete the force subscribe message
            try:
                await callback_query.message.delete()
            except:
                pass
            return
        
        # Add participant
        Giveaway.add_participant(giveaway["giveaway_id"], user_id)
        
        # Add user to database if not exists
        from database.models import User
        User.add_user(user_id, callback_query.from_user.username)
        
        participants_count = Giveaway.get_participants_count(giveaway["giveaway_id"])
        
        # Notify log group
        # await notification_service.notify_giveaway_participation(
        #     user_id,
        #     callback_query.from_user.username,
        #     giveaway["giveaway_id"],
        #     giveaway["prize"]
        # )
        
        # Show success message
        success_msg = f"🎉 Successfully joined!\n\n"
        success_msg += f"🎁 Prize: {giveaway['prize']}\n"
        success_msg += f"👥 Participants: {participants_count}"
        
        await callback_query.answer(success_msg, show_alert=True)
        
        # Delete the force subscribe message
        try:
            await callback_query.message.delete()
        except:
            pass
        
        logger.info(f"User {user_id} joined giveaway {giveaway['giveaway_id']} after force subscribe check")
