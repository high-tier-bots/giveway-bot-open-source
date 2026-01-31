from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def join_giveaway_keyboard():
    """Join giveaway button"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎁 Join Giveaway", callback_data="join_giveaway")]
    ])

def force_subscribe_keyboard(channels):
    """Force subscribe channels keyboard"""
    buttons = []
    for channel in channels:
        # Handle both old format (int) and new format (dict)
        if isinstance(channel, dict):
            username = channel.get("username", "")
            title = channel.get("title", "Channel")
            channel_id = channel.get("id")
        else:
            # Old format - just an integer, can't create proper button
            username = None
            channel_id = channel
            title = "Channel"
        
        if username:
            # Remove @ if present
            username_clean = username.lstrip('@')
            buttons.append([InlineKeyboardButton(f"📢 Join {title}", url=f"https://t.me/{username_clean}")])
    
    buttons.append([InlineKeyboardButton("✅ Try Again", callback_data="check_subscription")])
    return InlineKeyboardMarkup(buttons)

def admin_panel_keyboard():
    """Admin panel keyboard"""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🎁 Giveaway", callback_data="admin_giveaway"),
            InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast")
        ],
        [
            InlineKeyboardButton("⚙️ Settings", callback_data="admin_settings"),
            InlineKeyboardButton("📊 Stats", callback_data="admin_stats")
        ]
    ])

def giveaway_admin_keyboard(giveaway_id):
    """Giveaway admin control keyboard"""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🏁 End Giveaway", callback_data=f"end_giveaway_{giveaway_id}"),
            InlineKeyboardButton("🔄 Reroll", callback_data=f"reroll_giveaway_{giveaway_id}")
        ],
        [
            InlineKeyboardButton("👥 Participants", callback_data=f"participants_{giveaway_id}")
        ]
    ])

def broadcast_target_keyboard():
    """Broadcast target selection keyboard"""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("👤 Users", callback_data="broadcast_users"),
            InlineKeyboardButton("👥 Groups", callback_data="broadcast_groups")
        ],
        [
            InlineKeyboardButton("📢 Channels", callback_data="broadcast_channels"),
            InlineKeyboardButton("🌐 All", callback_data="broadcast_all")
        ],
        [InlineKeyboardButton("❌ Cancel", callback_data="cancel_broadcast")]
    ])

def settings_keyboard():
    """Settings keyboard"""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔔 Force Subscribe", callback_data="setting_force_subscribe"),
            InlineKeyboardButton("📢 Channels", callback_data="setting_channels")
        ],
        [
            InlineKeyboardButton("👮 Admins", callback_data="setting_admins"),
            InlineKeyboardButton("📝 Log Group", callback_data="setting_log_group")
        ],
        [InlineKeyboardButton("🔙 Back", callback_data="admin_panel")]
    ])

def confirm_keyboard(action):
    """Confirmation keyboard"""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Yes", callback_data=f"confirm_{action}"),
            InlineKeyboardButton("❌ No", callback_data=f"cancel_{action}")
        ]
    ])

def close_keyboard():
    """Close button"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ Close", callback_data="close")]
    ])

def end_giveaway_keyboard(giveaway_id):
    """End giveaway options keyboard"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Auto Announce", callback_data=f"end_auto_announce_{giveaway_id}")],
        [InlineKeyboardButton("⏳ Manual Announce", callback_data=f"end_manual_announce_{giveaway_id}")]
    ])

def announce_winner_keyboard(giveaway_id):
    """Announce winner button"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Announce Winners", callback_data=f"announce_winner_{giveaway_id}")]
    ])
