from flask import Blueprint, jsonify, request
from .db import get_db_connection, query_to_dict
from .mail_utils import generate_mail_from_transaction, generate_promotional_mail
from .auth_utils import token_required
import json

bp = Blueprint("email", __name__)


@bp.route("/generate_all_mails", methods=["POST"])
@token_required
def generate_all_mails():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM bank_accounts;")
    accounts = query_to_dict(cursor)
    accounts_map = {a["account_no"]: a for a in accounts}

    cursor.execute("SELECT * FROM bank_transactions;")
    txns = query_to_dict(cursor)

    created_ids = []

    for txn in txns:
        account = accounts_map.get(txn["account_no"])
        if account:
            mail_id = generate_mail_from_transaction(txn, account)
            created_ids.append(mail_id)

    for account in accounts:
        mail_id = generate_promotional_mail(account)
        created_ids.append(mail_id)

    cursor.close()
    conn.close()
    return jsonify({"status": "success", "created_mails": created_ids})


@bp.route("/mails", methods=["GET"])
@token_required
def get_mails_for_user():
    username = request.user.get("username")

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT m.* FROM mails m
        JOIN bank_accounts a ON m.account_no = a.account_no
        JOIN auth_users u ON u.account_no = a.account_no
        WHERE u.username = %s
        ORDER BY m.created_at DESC;
    """, (username,))
    rows = query_to_dict(cursor)
    cursor.close()
    conn.close()

    return jsonify(rows)

@bp.route("/mails/<int:mail_id>/read", methods=["PATCH"])
@token_required
def mark_mail_read(mail_id):
    username = request.user.get("username")
    is_read = request.json.get("is_read", True)

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE mails m
        SET is_read = %s
        FROM bank_accounts a, auth_users u
        WHERE m.account_no = a.account_no
          AND a.account_no = u.account_no
          AND u.username = %s
          AND m.id = %s
        RETURNING m.id, m.is_read;
    """, (is_read, username, mail_id))

    updated = cursor.fetchone()
    conn.commit()
    cursor.close()
    conn.close()

    if updated:
        return jsonify({"status": "success", "mail": {"id": updated[0], "is_read": updated[1]}})
    return jsonify({"status": "error", "message": "Mail not found or not yours"}), 404


@bp.route("/mails/<int:mail_id>/favourite", methods=["PATCH"])
@token_required
def toggle_favourite(mail_id):
    is_favourite = request.json.get("is_favourite")
    if is_favourite is None:
        return jsonify({"error": "Missing is_favourite field"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE mails SET is_favourite = %s WHERE id = %s RETURNING id, is_favourite;",
        (is_favourite, mail_id)
    )
    updated = cursor.fetchone()
    conn.commit()
    cursor.close()
    conn.close()

    if not updated:
        return jsonify({"error": "Mail not found"}), 404
    return jsonify({"id": updated[0], "is_favourite": updated[1]})


@bp.route("/mails/mark_read_bulk", methods=["PATCH"])
@token_required
def mark_read_bulk():
    mail_ids = request.json.get("ids", [])
    if not mail_ids:
        return jsonify({"error": "No mail IDs provided"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE mails SET is_read = TRUE WHERE id = ANY(%s) RETURNING id;",
        (mail_ids,)
    )
    updated = [row[0] for row in cursor.fetchall()]
    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({"updated_ids": updated})

@bp.route("/mails/send", methods=["POST"])
@token_required
def send_mail():
    data = request.get_json()
    sender_user = request.user  # from token_required decorator

    to_emails = data.get("to")
    if isinstance(to_emails, str):
        to_emails = [to_emails]  # make it a list

    cc_emails = data.get("cc", [])
    bcc_emails = data.get("bcc", [])
    subject = data.get("subject")
    body = data.get("body")
    attachments = data.get("attachments", [])

    if not to_emails or not subject or not body:
        return jsonify({"error": "to, subject, and body are required"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # get sender account_no
        cursor.execute("SELECT account_no FROM auth_users WHERE id = %s", (sender_user["user_id"],))
        sender_account_no = cursor.fetchone()[0]

        # function to map emails to account numbers
        def emails_to_accounts(emails):
            if not emails:
                return []
            cursor.execute(
                "SELECT account_no FROM auth_users WHERE email = ANY(%s)",
                (emails,)
            )
            return [row[0] for row in cursor.fetchall()]

        to_accounts = emails_to_accounts(to_emails)
        cc_accounts = emails_to_accounts(cc_emails)
        bcc_accounts = emails_to_accounts(bcc_emails)

        # insert mail for each recipient (Inbox)
        all_recipients = to_accounts + cc_accounts + bcc_accounts
        for recipient_account_no in all_recipients:
            cursor.execute(
                "SELECT username FROM auth_users WHERE account_no = %s",
                (recipient_account_no,)
            )
            recipient_username = cursor.fetchone()[0]

            cursor.execute("""
                INSERT INTO mails
                (account_no, sender_account_no, sender, receiver, subject, body, attachments, is_read, is_favourite, is_spam, is_important)
                VALUES (%s, %s, %s, %s, %s, %s, %s, FALSE, FALSE, FALSE, FALSE)
            """, (
                recipient_account_no,
                sender_account_no,
                sender_user["username"],
                recipient_username,
                subject,
                body,
                attachments
            ))

        conn.commit()
        return jsonify({"status": "success", "message": "Mail sent successfully."})

    except Exception as e:
        conn.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        cursor.close()
        conn.close()
