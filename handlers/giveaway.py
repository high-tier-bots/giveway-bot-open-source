from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery
from pyrogram import ContinuePropagation
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
    
    # Register command handlers FIRST with higher priority (group 0)
    # Register command handler for both /endgiveaway and /endgiveway
    @app.on_message(filters.command("endgiveaway") & filters.private, group=0)
    async def end_giveaway_endgiveaway(client: Client, message: Message):
        logger.info(f"[ROUTE] /endgiveaway command received from {message.from_user.id}")
        await end_giveaway_handler(client, message)
    
    @app.on_message(filters.command("endgiveway") & filters.private, group=0)
    async def end_giveaway_endgiveway(client: Client, message: Message):
        logger.info(f"[ROUTE] /endgiveway command received from {message.from_user.id}")
        await end_giveaway_handler(client, message)
    
    # Log all incoming messages for debugging (lower priority group 5)
    @app.on_message(filters.private, group=5)
    async def log_all_messages(client: Client, message: Message):
        if message.text and not message.command:
            logger.info(f"[MSG_DEBUG] Received message: '{message.text}' from user {message.from_user.id}")
        # Continue to other handlers
        raise ContinuePropagation()
    
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
    
    async def end_giveaway_handler(client: Client, message: Message):
        """Handle end giveaway command"""
        try:
            user_id = message.from_user.id
            admins = Settings.get_admins()
            
            logger.info(f"[END_GIVEAWAY_CMD] Checking admin status for user {user_id}")
            logger.info(f"[END_GIVEAWAY_CMD] Admin list: {admins}")
            
            if user_id not in admins:
                logger.warning(f"[END_GIVEAWAY_CMD] User {user_id} is not an admin")
                await message.reply_text("❌ This command is only for admins!")
                return
            
            logger.info(f"[END_GIVEAWAY_CMD] Admin {user_id} initiated end giveaway command")
            
            giveaway = Giveaway.get_active_giveaway()
            if not giveaway:
                logger.warning(f"[END_GIVEAWAY_CMD] No active giveaway found")
                await message.reply_text("❌ No active giveaway to end!")
                return
            
            logger.info(f"[END_GIVEAWAY_CMD] Found active giveaway: {giveaway['giveaway_id']}")
            
            # Show options: Auto announce or manual
            from utils.inline import end_giveaway_keyboard
            await message.reply_text(
                "🎁 **End Giveaway Options:**\n\n"
                "Choose how you want to end the giveaway:",
                reply_markup=end_giveaway_keyboard(giveaway["giveaway_id"])
            )
            logger.info(f"[END_GIVEAWAY_CMD] Options keyboard sent for giveaway {giveaway['giveaway_id']}")
        except Exception as e:
            logger.error(f"[END_GIVEAWAY_CMD] Error: {str(e)}", exc_info=True)
            await message.reply_text(f"❌ Error: {str(e)}")
    
    async def end_giveaway(client: Client, giveaway, ended_by=None, auto_announce=True):
        """End a giveaway and select winners"""
        try:
            giveaway_id = giveaway["giveaway_id"]
            participants = giveaway.get("participants", [])
            winners_count = giveaway["winners_count"]
            
            logger.info(f"[END_GIVEAWAY] Starting end_giveaway process for {giveaway_id}")
            logger.info(f"[END_GIVEAWAY] Participants: {len(participants)}, Winners needed: {winners_count}, Auto-announce: {auto_announce}")
            
            if len(participants) == 0:
                # No participants
                logger.warning(f"[END_GIVEAWAY] No participants for giveaway {giveaway_id}")
                Giveaway.end_giveaway(giveaway_id)
                result_text = f"🏁 **Giveaway Ended**\n\n"
                result_text += f"🎁 **Prize:** {giveaway['prize']}\n"
                result_text += f"❌ **No participants!**"
                
                # Notify users
                from database.models import User
                users = User.get_all_users()
                logger.info(f"[END_GIVEAWAY] Notifying {len(users)} users about no participants")
                for user in users:
                    try:
                        await client.send_message(user["user_id"], result_text)
                    except Exception as e:
                        logger.debug(f"[END_GIVEAWAY] Failed to notify user {user['user_id']}: {e}")
                
                logger.info(f"[END_GIVEAWAY] Giveaway {giveaway_id} ended with no participants")
                return
            
            # Select winners
            logger.info(f"[END_GIVEAWAY] Selecting {winners_count} winners from {len(participants)} participants")
            winners = select_random_winners(participants, winners_count)
            logger.info(f"[END_GIVEAWAY] Selected winners: {winners}")
            
            # Update giveaway status and winners in database
            logger.info(f"[END_GIVEAWAY] Updating database for giveaway {giveaway_id}")
            Giveaway.end_giveaway(giveaway_id, winners)
            logger.info(f"[END_GIVEAWAY] Database updated successfully")
            
            if auto_announce:
                logger.info(f"[END_GIVEAWAY] Starting auto-announce process")
                # Prepare winner announcement
                result_text = f"🏁 **Giveaway Ended!**\n\n"
                result_text += f"🎁 **Prize:** {giveaway['prize']}\n"
                result_text += f"👥 **Participants:** {len(participants)}\n\n"
                result_text += f"🎉 **Winners:**\n"
                
                for winner_id in winners:
                    try:
                        winner_user = await client.get_users(winner_id)
                        result_text += f"  🏆 {get_user_mention(winner_user)}\n"
                        logger.debug(f"[END_GIVEAWAY] Retrieved winner info: {winner_user.username or winner_id}")
                    except Exception as e:
                        logger.debug(f"[END_GIVEAWAY] Could not retrieve winner {winner_id}: {e}")
                        result_text += f"  🏆 User {winner_id}\n"
                
                result_text += f"\n🎊 Congratulations to all winners!"
                
                # Notify all participants
                logger.info(f"[END_GIVEAWAY] Notifying {len(participants)} participants of winners")
                success_count = 0
                for participant_id in participants:
                    try:
                        await client.send_message(participant_id, result_text, disable_web_page_preview=True)
                        success_count += 1
                    except Exception as e:
                        logger.error(f"[END_GIVEAWAY] Failed to notify participant {participant_id}: {e}")
                
                logger.info(f"[END_GIVEAWAY] Successfully notified {success_count}/{len(participants)} participants")
                
                # Update status to announced
                logger.info(f"[END_GIVEAWAY] Updating status to announced")
                Giveaway.update_giveaway_status(giveaway_id, "announced")
                
                logger.info(f"[END_GIVEAWAY] ✅ Giveaway {giveaway_id} ended with {len(winners)} winners (auto-announced)")
            else:
                logger.info(f"[END_GIVEAWAY] Manual announcement mode - winners selected but not announced yet")
                logger.info(f"[END_GIVEAWAY] ✅ Giveaway {giveaway_id} ended with {len(winners)} winners (pending manual announcement)")
        except Exception as e:
            logger.error(f"[END_GIVEAWAY] Critical error in end_giveaway: {str(e)}", exc_info=True)
            raise
    
    @app.on_callback_query(filters.regex("^end_auto_announce_"))
    async def end_auto_announce_callback(client: Client, callback_query: CallbackQuery):
        """End giveaway and automatically announce winner"""
        try:
            # Extract giveaway_id: "end_auto_announce_GA_20260131063210_2963" -> "GA_20260131063210_2963"
            giveaway_id = callback_query.data.replace("end_auto_announce_", "")
            logger.info(f"[AUTO_ANNOUNCE] User {callback_query.from_user.id} clicked auto announce for giveaway {giveaway_id}")
            
            giveaway = Giveaway.get_giveaway(giveaway_id)
            
            if not giveaway:
                logger.error(f"[AUTO_ANNOUNCE] Giveaway {giveaway_id} not found")
                await callback_query.answer("❌ Giveaway not found!", show_alert=True)
                return
            
            logger.info(f"[AUTO_ANNOUNCE] Processing auto announcement for {giveaway_id}")
            await callback_query.message.delete()
            
            await end_giveaway(client, giveaway, callback_query.from_user.id, auto_announce=True)
            
            logger.info(f"[AUTO_ANNOUNCE] ✅ Successfully processed auto announce for {giveaway_id}")
            await callback_query.answer("✅ Giveaway ended and winners announced!", show_alert=True)
        except Exception as e:
            logger.error(f"[AUTO_ANNOUNCE] Error: {str(e)}", exc_info=True)
            await callback_query.answer(f"❌ Error: {str(e)}", show_alert=True)
    
    @app.on_callback_query(filters.regex("^end_manual_announce_"))
    async def end_manual_announce_callback(client: Client, callback_query: CallbackQuery):
        """End giveaway and wait for manual announcement"""
        try:
            # Extract giveaway_id: "end_manual_announce_GA_20260131063210_2963" -> "GA_20260131063210_2963"
            giveaway_id = callback_query.data.replace("end_manual_announce_", "")
            logger.info(f"[MANUAL_ANNOUNCE] User {callback_query.from_user.id} clicked manual announce for giveaway {giveaway_id}")
            
            giveaway = Giveaway.get_giveaway(giveaway_id)
            
            if not giveaway:
                logger.error(f"[MANUAL_ANNOUNCE] Giveaway {giveaway_id} not found")
                await callback_query.answer("❌ Giveaway not found!", show_alert=True)
                return
            
            logger.info(f"[MANUAL_ANNOUNCE] Processing manual announcement mode for {giveaway_id}")
            await callback_query.message.delete()
            
            await end_giveaway(client, giveaway, callback_query.from_user.id, auto_announce=False)
            
            # Store the giveaway in pending state for manual announcement
            logger.info(f"[MANUAL_ANNOUNCE] Updating status to pending_announcement")
            Giveaway.update_giveaway_status(giveaway_id, "pending_announcement")
            
            from utils.inline import announce_winner_keyboard
            await callback_query.from_user.send_message(
                f"🎁 **Giveaway Ended - Pending Announcement**\n\n"
                f"Prize: {giveaway['prize']}\n"
                f"Participants: {len(giveaway.get('participants', []))}\\n"
                f"Use the button below to announce the winner:",
                reply_markup=announce_winner_keyboard(giveaway_id)
            )
            
            logger.info(f"[MANUAL_ANNOUNCE] ✅ Successfully set up manual announcement for {giveaway_id}")
            await callback_query.answer("✅ Giveaway ended! Use button to announce winner.", show_alert=True)
        except Exception as e:
            logger.error(f"[MANUAL_ANNOUNCE] Error: {str(e)}", exc_info=True)
            await callback_query.answer(f"❌ Error: {str(e)}", show_alert=True)
    
    @app.on_callback_query(filters.regex("^announce_winner_"))
    async def announce_winner_callback(client: Client, callback_query: CallbackQuery):
        """Announce winner for a giveaway"""
        try:
            # Extract giveaway_id: "announce_winner_GA_20260131063210_2963" -> "GA_20260131063210_2963"
            giveaway_id = callback_query.data.replace("announce_winner_", "")
            logger.info(f"[ANNOUNCE_WINNER] User {callback_query.from_user.id} clicked announce winner for giveaway {giveaway_id}")
            
            giveaway = Giveaway.get_giveaway(giveaway_id)
            
            if not giveaway:
                logger.error(f"[ANNOUNCE_WINNER] Giveaway {giveaway_id} not found")
                await callback_query.answer("❌ Giveaway not found!", show_alert=True)
                return
            
            if not giveaway.get("winners"):
                logger.warning(f"[ANNOUNCE_WINNER] No winners selected for giveaway {giveaway_id}")
                await callback_query.answer("❌ No winners selected for this giveaway!", show_alert=True)
                return
            
            logger.info(f"[ANNOUNCE_WINNER] Found {len(giveaway['winners'])} winners for {giveaway_id}")
            await callback_query.message.delete()
            
            # Send winner announcement
            result_text = f"🏁 **Giveaway Ended!**\n\n"
            result_text += f"🎁 **Prize:** {giveaway['prize']}\n"
            result_text += f"👥 **Participants:** {len(giveaway.get('participants', []))}\n\n"
            result_text += f"🎉 **Winners:**\n"
            
            winners = giveaway.get("winners", [])
            for winner_id in winners:
                try:
                    winner_user = await client.get_users(winner_id)
                    result_text += f"  🏆 {get_user_mention(winner_user)}\n"
                    logger.debug(f"[ANNOUNCE_WINNER] Retrieved winner: {winner_user.username or winner_id}")
                except Exception as e:
                    logger.debug(f"[ANNOUNCE_WINNER] Could not retrieve winner {winner_id}: {e}")
                    result_text += f"  🏆 User {winner_id}\n"
            
            result_text += f"\n🎊 Congratulations to all winners!"
            
            # Notify all participants
            participants = giveaway.get("participants", [])
            logger.info(f"[ANNOUNCE_WINNER] Notifying {len(participants)} participants about winners")
            success_count = 0
            for participant_id in participants:
                try:
                    await client.send_message(participant_id, result_text, disable_web_page_preview=True)
                    success_count += 1
                except Exception as e:
                    logger.error(f"[ANNOUNCE_WINNER] Failed to notify participant {participant_id}: {e}")
            
            logger.info(f"[ANNOUNCE_WINNER] Successfully notified {success_count}/{len(participants)} participants")
            
            # Update giveaway status
            logger.info(f"[ANNOUNCE_WINNER] Updating status to announced")
            Giveaway.update_giveaway_status(giveaway_id, "announced")
            
            logger.info(f"[ANNOUNCE_WINNER] ✅ Winners announced for giveaway {giveaway_id}")
            await callback_query.answer("✅ Winners announced to all participants!", show_alert=True)
        except Exception as e:
            logger.error(f"[ANNOUNCE_WINNER] Error: {str(e)}", exc_info=True)
            await callback_query.answer(f"❌ Error: {str(e)}", show_alert=True)
    
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
