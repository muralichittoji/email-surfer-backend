from flask import Blueprint, jsonify, request, send_from_directory

from app.mail_utils import generate_mail_from_transaction, generate_promotional_mail
from .db import get_db_connection, query_to_dict
from .auth_utils import token_required
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import uuid, os, hashlib, json

bp = Blueprint("email", __name__)

# PDF storage directory (safe path)
PDF_DIR = os.path.join(os.path.dirname(__file__), "./transaction_pdfs/")
os.makedirs(PDF_DIR, exist_ok=True)

@bp.route("/generate_all_mails", methods=["POST"])
def generate_all_mails():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Get all accounts
    cursor.execute("SELECT * FROM bank_accounts;")
    accounts = query_to_dict(cursor)
    accounts_map = {a["account_no"]: a for a in accounts}

    # Get all transactions
    cursor.execute("SELECT * FROM bank_transactions;")
    txns = query_to_dict(cursor)

    created_ids = []

    # Generate transactional emails
    for txn in txns:
        account = accounts_map.get(txn["account_no"])
        if account:
            mail_id = generate_mail_from_transaction(txn, account)
            created_ids.append(mail_id)

    # Generate promotional emails
    for account in accounts:
        mail_id = generate_promotional_mail(account)
        created_ids.append(mail_id)

    cursor.close()
    conn.close()

    return jsonify({
        "status": "success",
        "created_email_cases": created_ids
    })


# ---------------------------
# Create Email Case (Send)
# ---------------------------
@bp.route("/mails/send", methods=["POST"])
@token_required
def send_email_case():
    data = request.get_json()
    sender_user = request.user

    from_addr = sender_user.get("email")
    to_addr = data.get("to_addr")
    subject = data.get("subject")
    body = data.get("body")
    router = data.get("router", "default")
    top_label = data.get("top_label")
    top_score = data.get("top_score")
    top_categories = data.get("top_categories", {})
    entities = data.get("entities", {})
    body_lang = data.get("body_lang", "en")

    if not to_addr or not subject or not body:
        return jsonify({"error": "to_addr, subject, and body are required"}), 400

    case_id = str(uuid.uuid4())

    # Generate PDF
    pdf_filename = f"{case_id}.pdf"
    pdf_path = os.path.join(PDF_DIR, pdf_filename)
    c = canvas.Canvas(pdf_path, pagesize=letter)
    c.drawString(100, 750, f"From: {from_addr}")
    c.drawString(100, 735, f"To: {to_addr}")
    c.drawString(100, 720, f"Subject: {subject}")
    c.drawString(100, 700, "------------------------------------")
    # Handle multi-line body
    text = c.beginText(100, 680)
    for line in body.split("\n"):
        for i in range(0, len(line), 100):  # wrap every 100 chars
            text.textLine(line[i:i+100])
    c.drawText(text)
    c.save()

    # Compute SHA256 for PDF
    with open(pdf_path, "rb") as f:
        pdf_sha256 = hashlib.sha256(f.read()).hexdigest()

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO email_cases (
              case_id, from_addr, to_addr, subject, body_lang, router,
              top_label, top_score, top_categories, entities,
              status, pdf_sha256
            )
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'received',%s)
            RETURNING id;
        """, (
            case_id, from_addr, to_addr, subject, body_lang, router,
            top_label, top_score, json.dumps(top_categories),
            json.dumps(entities), pdf_sha256
        ))
        conn.commit()
        return jsonify({
            "status": "success",
            "message": "Email sent successfully",
            "case_id": case_id,
            "pdf_sha256": pdf_sha256
        })
    except Exception as e:
        conn.rollback()
        return jsonify({"status": "error", "message": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

# ---------------------------
# Fetch All Emails for Logged-in User
# ---------------------------
@bp.route("/mails", methods=["GET"])
@token_required
def get_mails_for_user():
    username = request.user.get("username")
    if not username:
        return jsonify({"error": "Username not found in token"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT email FROM auth_users WHERE username = %s;", (username,))
    email_row = cursor.fetchone()
    if not email_row:
        return jsonify({"error": "Email not found in DB"}), 404
    user_email = email_row[0]
    print("Logged-in user email:", user_email)
    cursor.execute("""
        SELECT *
        FROM email_cases
        WHERE from_addr = %s OR to_addr = %s
        ORDER BY created_at DESC;
    """, (user_email, user_email))
    rows = query_to_dict(cursor)
    cursor.close()
    conn.close()
    return jsonify(rows)



# ---------------------------
# Fetch Single Email Case
# ---------------------------
@bp.route("/mails/<string:case_id>", methods=["GET"])
@token_required
def get_email_case(case_id):
    user_email = request.user.get("email")

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM email_cases
        WHERE case_id = %s AND (from_addr = %s OR to_addr = %s)
    """, (case_id, user_email, user_email))
    rows = query_to_dict(cursor)
    cursor.close()
    conn.close()

    if not rows:
        return jsonify({"error": "Email case not found"}), 404

    return jsonify(rows[0])

# ---------------------------
# Download PDF for a Case
# ---------------------------
@bp.route("/mails/pdf/<string:pdf_sha256>", methods=["GET"])
@token_required
def download_pdf_by_hash(pdf_sha256):
    username = request.user.get("username")
    if not username:
        return jsonify({"error": "Username not found in token"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get user email from username
    cursor.execute("SELECT email FROM auth_users WHERE username = %s;", (username,))
    email_row = cursor.fetchone()
    if not email_row:
        cursor.close()
        conn.close()
        return jsonify({"error": "Email not found in DB"}), 404
    user_email = email_row[0]
    print("Logged-in user email:", user_email)

    # Now get case_id matching hash and user's email
    cursor.execute("""
        SELECT case_id 
        FROM email_cases
        WHERE pdf_sha256 = %s AND (from_addr = %s OR to_addr = %s)
    """, (pdf_sha256, user_email, user_email))
    row = cursor.fetchone()
    cursor.close()
    conn.close()

    if not row:
        return jsonify({"error": "PDF not found"}), 404

    case_id = row[0]  # UUID that matches the file name
    pdf_path = os.path.join(PDF_DIR, f"{case_id}.pdf")

    if not os.path.exists(pdf_path):
        print(f"PDF not found on disk: {pdf_path}")
        return jsonify({"error": "PDF file missing on server"}), 404

    print(f"Serving PDF for case_id={case_id}, hash={pdf_sha256}")
    return send_from_directory(PDF_DIR, f"{case_id}.pdf", as_attachment=False)
