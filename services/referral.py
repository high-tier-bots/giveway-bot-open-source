from database.models import User

class ReferralService:
    @staticmethod
    def get_referral_link(bot_username: str, user_id: int) -> str:
        """Generate referral link for user"""
        return f"https://t.me/{bot_username}?start=ref_{user_id}"
    
    @staticmethod
    def extract_referrer_id(start_param: str) -> int:
        """Extract referrer ID from start parameter"""
        if start_param and start_param.startswith("ref_"):
            try:
                return int(start_param.split("_")[1])
            except (IndexError, ValueError):
                return None
        return None
    
    @staticmethod
    def get_referral_stats(user_id: int) -> dict:
        """Get referral statistics for user"""
        user = User.get_user(user_id)
        if not user:
            return {"total_referrals": 0, "referrals": []}
        
        referrals = user.get("referrals", [])
        return {
            "total_referrals": len(referrals),
            "referrals": referrals
        }
