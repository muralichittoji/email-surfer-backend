from flask import Blueprint, request, jsonify
from .db import get_db_connection, query_to_dict
import jwt
import datetime
import os
from .utils import hash_password, verify_password

bp = Blueprint("auth", __name__)

SECRET_KEY = os.getenv("SECRET_KEY")
DEFAULT_PASSWORD = os.getenv("DEFAULT_PASSWORD")

@bp.route("/auth/check_user", methods=["POST"])
def check_user():
    data = request.get_json()
    username_or_email = data.get("username_email")

    if not username_or_email:
        return jsonify({"error": "username or email is required"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT username, email FROM auth_users
        WHERE username = %s OR email = %s
    """, (username_or_email, username_or_email))

    user = cursor.fetchone()
    cursor.close()
    conn.close()

    if user:
        return jsonify({"exists": True, "username": user[0], "email": user[1]})
    else:
        return jsonify({"exists": False})



@bp.route("/auth/login", methods=["POST"])
def login():
    data = request.get_json()
    username_or_email = data.get("username_email")
    password = data.get("password")

    if not username_or_email or not password:
        return jsonify({"error": "Both fields are required"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, username, email, password FROM auth_users
        WHERE username = %s OR email = %s
    """, (username_or_email, username_or_email))

    user = cursor.fetchone()
    cursor.close()
    conn.close()

    if user and verify_password(password, user[3]):
        payload = {
            "user_id": user[0],
            "username": user[1],
            "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=8)
        }
        token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")

        return jsonify({
            "status": "success",
            "token": token,
            "username": user[1],
            "email": user[2]
        })

    return jsonify({"status": "error", "message": "Invalid credentials"}), 401


@bp.route("/bank_logins", methods=["POST", "OPTIONS"])
def populate_auth_users():
    if request.method == "OPTIONS":
        # Respond to preflight request
        return jsonify({"message": "Preflight OK"}), 200

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT DISTINCT account_no, customer_name FROM bank_accounts;")
    customers = query_to_dict(cursor)

    try:
        for customer in customers:
            account_no = customer["account_no"]
            name = customer["customer_name"]
            username = name.lower().replace(" ", "")
            email = f"{username}@gmail.com"
            hashed_password = hash_password(DEFAULT_PASSWORD)

            cursor.execute("""
                INSERT INTO auth_users (account_no, username, email, password)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (account_no) DO NOTHING;
            """, (account_no, username, email, hashed_password))

        conn.commit()
    except Exception as e:
        conn.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

    return jsonify({"status": "success", "message": "Auth users populated successfully."})
