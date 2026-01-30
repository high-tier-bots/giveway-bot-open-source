import os
from dotenv import load_dotenv

load_dotenv()

class Config:
  # ============================================================================
  # REQUIRED CONFIGURATIONS - Must be set in .env file
  # ============================================================================

  # Telegram API credentials (REQUIRED)
  API_ID = int(os.getenv("API_ID"))
  API_HASH = os.getenv("API_HASH")
  BOT_TOKEN = os.getenv("BOT_TOKEN")

  # Database configuration (REQUIRED)
  DB_URL = os.getenv("DB_URL")
  DB_NAME = os.getenv("DB_NAME")

  # Channel and admin configuration (REQUIRED)
  LOG_CHANNEL = int(os.getenv("LOG_CHANNEL"))
  ADMINS = [int(admin_id) for admin_id in os.getenv("ADMINS", "").split(",") if admin_id.strip()]

  # ============================================================================
  # OPTIONAL CONFIGURATIONS - Have sensible defaults
  # ============================================================================

  # Feature flags (optional, defaults to True)
  FORCE_SUBSCRIBE = os.getenv("FORCE_SUBSCRIBE", "true").lower() == "true"
  FORCE_CHANNEL = os.getenv("FORCE_CHANNEL", "true").lower() == "true"

  # Developer information (optional)
  DEVELOPER_NAME = os.getenv("DEVELOPER_NAME", "YourName")
  DEVELOPER_CONTACT = os.getenv("DEVELOPER_CONTACT", "https://t.me/yourtelegram")

  # Bot UI and channel configuration (optional)
  STARTER_PIC = os.getenv("STARTER_PIC", "https://example.com/default_image.jpg")
  UPDATE_CHANNEL = os.getenv("UPDATE_CHANNEL", "")
  SUPPORT_CHANNEL = os.getenv("SUPPORT_CHANNEL", "")
