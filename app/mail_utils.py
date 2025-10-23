import random, uuid, os, hashlib, json
from datetime import datetime
from .db import get_db_connection
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

PDF_DIR = os.path.join(os.path.dirname(__file__), "transaction_pdfs")
os.makedirs(PDF_DIR, exist_ok=True)

# -------------------------
# Transaction-based Email Case
# -------------------------
def generate_mail_from_transaction(txn, account):
    acc_last4 = str(account["account_no"]).zfill(4)[-4:]
    amount = f"₹{txn['amount']}"
    txn_time = txn["txn_ts"]

    subject = f"{amount} {'credited to' if txn['txn_type'].upper() == 'CREDIT' else 'debited from'} your account {acc_last4}"

    body = f"""
Dear {account['customer_name']},

An amount of {amount} has been {txn['txn_type'].upper()} to your account ending with {acc_last4} on {txn_time} via {txn['channel']} transaction at {txn['merchant']}.

Transaction Details:
- Transaction ID: {txn['txn_id']}
- Channel: {txn['channel']}
- Merchant: {txn['merchant']}
- Description: {txn['description']}
- Amount: {amount}
- Type: {txn['txn_type']}

Thank you for banking with Bank India.

Regards,
Bank India
"""

    case_id = str(uuid.uuid4())
    pdf_filename = f"{case_id}.pdf"
    pdf_path = os.path.join(PDF_DIR, pdf_filename)

    # Create PDF
    c = canvas.Canvas(pdf_path, pagesize=letter)
    c.drawString(100, 750, f"From: bank@bankindia.com")
    c.drawString(100, 735, f"To: {account['customer_name']} <{account['email']}>")
    c.drawString(100, 720, f"Subject: {subject}")
    c.drawString(100, 700, "-"*50)
    text = c.beginText(100, 680)
    for line in body.split("\n"):
        for i in range(0, len(line), 100):
            text.textLine(line[i:i+100])
    c.drawText(text)
    c.save()

    # Compute SHA256
    with open(pdf_path, "rb") as f:
        pdf_sha256 = hashlib.sha256(f.read()).hexdigest()

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO email_cases (
            case_id, from_addr, to_addr, subject, body_lang, router,
            top_label, top_score, top_categories, entities,
            status, pdf_sha256
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'received',%s)
        RETURNING id;
    """, (
        case_id,
        "bank@bankindia.com",
        account['email'],
        subject,
        "en",
        "transaction",
        None,
        None,
        json.dumps({}),
        json.dumps({}),
        pdf_sha256
    ))
    mail_id = cursor.fetchone()[0]
    conn.commit()
    cursor.close()
    conn.close()
    return mail_id


# -------------------------
# Promotional Email Cases
# -------------------------
PROMO_CATEGORIES = [
    {"subject": "Fixed Deposit Offer", "router": "promotions", "priority": 4},
    {"subject": "Home Loan Offer", "router": "promotions", "priority": 3},
    {"subject": "Car Loan Offer", "router": "promotions", "priority": 3},
]

def generate_promotional_mail(account):
    promo = random.choice(PROMO_CATEGORIES)
    subject = promo["subject"]
    router = promo["router"]
    body = f"""
Dear {account['customer_name']},

We have a special offer for you: {subject}.

Please contact your branch for more details.

Regards,
Bank India
"""

    case_id = str(uuid.uuid4())
    pdf_filename = f"{case_id}.pdf"
    pdf_path = os.path.join(PDF_DIR, pdf_filename)

    # Create PDF
    c = canvas.Canvas(pdf_path, pagesize=letter)
    c.drawString(100, 750, f"From: bank@bankindia.com")
    c.drawString(100, 735, f"To: {account['customer_name']} <{account['email']}>")
    c.drawString(100, 720, f"Subject: {subject}")
    c.drawString(100, 700, "-"*50)
    text = c.beginText(100, 680)
    for line in body.split("\n"):
        for i in range(0, len(line), 100):
            text.textLine(line[i:i+100])
    c.drawText(text)
    c.save()

    # Compute SHA256
    with open(pdf_path, "rb") as f:
        pdf_sha256 = hashlib.sha256(f.read()).hexdigest()

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO email_cases (
            case_id, from_addr, to_addr, subject, body_lang, router,
            top_label, top_score, top_categories, entities,
            status, pdf_sha256
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'received',%s)
        RETURNING id;
    """, (
        case_id,
        "bank@bankindia.com",
        account['email'],
        subject,
        "en",
        router,
        None,
        None,
        json.dumps({}),
        json.dumps({}),
        pdf_sha256
    ))
    mail_id = cursor.fetchone()[0]
    conn.commit()
    cursor.close()
    conn.close()
    return mail_id
