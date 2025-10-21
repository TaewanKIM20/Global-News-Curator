from flask import Flask
from shared.settings import settings
from shared.db import db
from flask_migrate import Migrate
from zoneinfo import ZoneInfo
from apscheduler.schedulers.background import BackgroundScheduler
from apps.api.scheduler.jobs import register_jobs
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]  # news-pipeline/
load_dotenv(ROOT / ".env")

migrate = Migrate()
scheduler = None  # 재시작시 중복 방지

def create_app():
    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY=settings.SECRET_KEY,
        SQLALCHEMY_DATABASE_URI=settings.SQLALCHEMY_DATABASE_URI,
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )

    db.init_app(app)
    migrate.init_app(app, db)

    # 블루프린트 등록
    from apps.api.routes.health import bp as health_bp
    app.register_blueprint(health_bp)

    # 스케줄러 시작 (리로더로 두 번 뜨는 문제 방지)
    global scheduler
    if scheduler is None:
        scheduler = BackgroundScheduler(timezone=ZoneInfo(settings.TIMEZONE))
        register_jobs(scheduler, app)
        scheduler.start()

    @app.get("/")
    def index():
        return "News Pipeline API"

    return app
