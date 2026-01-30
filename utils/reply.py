from pyrogram.types import ReplyKeyboardMarkup, KeyboardButton

def main_menu_keyboard(is_admin=False):
    """Main menu keyboard"""
    buttons = [
        [KeyboardButton("🎁 Active Giveaway"), KeyboardButton("📊 Stats")],
        [KeyboardButton("🏆 Winners"), KeyboardButton("❓ Help")]
    ]
    
    if is_admin:
        buttons.append([KeyboardButton("👮 Admin Panel")])
    
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

def admin_menu_keyboard():
    """Admin menu keyboard"""
    buttons = [
        [KeyboardButton("🎁 Create Giveaway"), KeyboardButton("🏁 End Giveaway")],
        [KeyboardButton("📢 Broadcast"), KeyboardButton("⚙️ Settings")],
        [KeyboardButton("📊 Statistics"), KeyboardButton("🔙 Back to Main")]
    ]
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

def cancel_keyboard():
    """Cancel operation keyboard"""
    return ReplyKeyboardMarkup(
        [[KeyboardButton("❌ Cancel")]],
        resize_keyboard=True
    )
