import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev")
    SQLALCHEMY_DATABASE_URI = os.getenv("SQLALCHEMY_DATABASE_URI", "sqlite:///news.sqlite3")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    TIMEZONE = os.getenv("TIMEZONE", "Asia/Seoul")
    FEEDS = [u.strip() for u in os.getenv("FEEDS", "").split(",") if u.strip()]
    
    USER_PREFERENCES = [p.strip().lower() for p in os.getenv("USER_PREFERENCES", "").split(",") if p.strip()]

settings = Settings()
