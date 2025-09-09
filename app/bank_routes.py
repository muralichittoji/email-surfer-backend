from flask import Blueprint, jsonify
from .db import get_db_connection, query_to_dict
import psycopg2
from .utils import hash_password

bp = Blueprint("bank", __name__)

@bp.route("/bank_accounts", methods=["GET"])
def get_bank_accounts():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM bank_accounts;")
    rows = query_to_dict(cursor)
    cursor.close()
    conn.close()
    return jsonify(rows)

@bp.route("/bank_transactions", methods=["GET"])
def get_bank_transactions():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM bank_transactions;")
    rows = query_to_dict(cursor)
    cursor.close()
    conn.close()
    return jsonify(rows)

DEFAULT_PASSWORD = "Otsi@12345"
@bp.route("/bank_logins", methods=["POST"])
def populate_auth_users():
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

            # Hash the default password before inserting
            hashed_password = hash_password(DEFAULT_PASSWORD)

            # Insert into auth_users with ON CONFLICT (account_no) DO NOTHING
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
