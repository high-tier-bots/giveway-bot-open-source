import random
from datetime import datetime
from pyrogram.types import User as PyrogramUser

def generate_giveaway_id():
    """Generate unique giveaway ID"""
    return f"GA_{datetime.now().strftime('%Y%m%d%H%M%S')}_{random.randint(1000, 9999)}"

def select_random_winners(participants, count):
    """Select random winners from participants"""
    if len(participants) <= count:
        return participants
    return random.sample(participants, count)

def format_time_remaining(end_time):
    """Format time remaining until end time"""
    if isinstance(end_time, str):
        end_time = datetime.fromisoformat(end_time)
    
    now = datetime.now()
    if end_time < now:
        return "Ended"
    
    delta = end_time - now
    days = delta.days
    hours, remainder = divmod(delta.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    if days > 0:
        return f"{days}d {hours}h {minutes}m"
    elif hours > 0:
        return f"{hours}h {minutes}m"
    else:
        return f"{minutes}m {seconds}s"

def get_user_mention(user: PyrogramUser):
    """Get user mention"""
    if user.username:
        return f"@{user.username}"
    return f"[{user.first_name}](tg://user?id={user.id})"

def format_datetime(dt):
    """Format datetime to readable string"""
    if isinstance(dt, str):
        dt = datetime.fromisoformat(dt)
    return dt.strftime("%Y-%m-%d %H:%M:%S")

def parse_time_string(time_str):
    """Parse time string like '1h', '30m', '2d' to seconds"""
    time_str = time_str.lower().strip()
    
    if time_str.endswith('d'):
        return int(time_str[:-1]) * 86400
    elif time_str.endswith('h'):
        return int(time_str[:-1]) * 3600
    elif time_str.endswith('m'):
        return int(time_str[:-1]) * 60
    else:
        return int(time_str)
