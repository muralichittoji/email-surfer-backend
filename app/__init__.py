from flask import Flask
from flask_cors import CORS
from apscheduler.schedulers.background import BackgroundScheduler
import os
from dotenv import load_dotenv

from app.bank_routes import bp as bank_bp
from app.mail_routes import bp as email_bp
from app.auth_routes import bp as auth_bp
from .mail_utils import generate_promotional_mail
from .db import get_db_connection, query_to_dict

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
DEFAULT_PASSWORD = os.getenv("DEFAULT_PASSWORD")


def generate_promotional_mail_for_all_accounts():
    print("[Scheduler] Starting promotional mail generation...")
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM bank_accounts;")
        accounts = query_to_dict(cursor)

        created_ids = [generate_promotional_mail(account) for account in accounts]
        print(f"[Scheduler] Generated promotional mails: {created_ids}")
    finally:
        cursor.close()
        conn.close()


def create_app():
    app = Flask(__name__)

    # THIS is crucial — Proper global CORS configuration
    CORS(
        app,
        resources={r"/*": {"origins": "*"}},
        supports_credentials=True,
        allow_headers=["Content-Type", "Authorization"],
        methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"]
    )

    app.register_blueprint(bank_bp)
    app.register_blueprint(email_bp)
    app.register_blueprint(auth_bp)

    if os.environ.get("WERKZEUG_RUN_MAIN") == "true" or not app.debug:
        scheduler = BackgroundScheduler()
        scheduler.add_job(
            func=generate_promotional_mail_for_all_accounts,
            trigger="interval",
            hours=24,
            id="promotional_mail_job",
            replace_existing=True
        )
        scheduler.start()
        print("[Scheduler] Started promotional mail scheduler.")

    return app
