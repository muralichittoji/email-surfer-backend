# generate_transaction_emails.py
import os
import uuid
import hashlib
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from db import get_db_connection, query_to_dict  # absolute import

PDF_DIR = "transaction_pdfs"
os.makedirs(PDF_DIR, exist_ok=True)

# -------------------------
# Generate PDF for a transaction
# -------------------------
def create_transaction_pdf(account, txn):
    case_id = str(uuid.uuid4())
    pdf_filename = f"{case_id}.pdf"
    pdf_path = os.path.join(PDF_DIR, pdf_filename)

    c = canvas.Canvas(pdf_path, pagesize=letter)
    c.drawString(100, 750, f"Account No: {account['account_no']}")
    c.drawString(100, 735, f"Customer: {account['customer_name']}")
    c.drawString(100, 720, f"Transaction ID: {txn['txn_id']}")
    c.drawString(100, 705, f"Amount: {txn['amount']}")
    c.drawString(100, 690, f"Type: {txn['txn_type']}")
    c.drawString(100, 675, f"Channel: {txn['channel']}")
    c.drawString(100, 660, f"Merchant: {txn['merchant']}")
    c.drawString(100, 645, f"Description: {txn['description']}")
    c.drawString(100, 630, f"Date: {txn['txn_ts']}")
    c.save()

    # SHA256 for PDF
    with open(pdf_path, "rb") as f:
        pdf_sha256 = hashlib.sha256(f.read()).hexdigest()

    return case_id, pdf_filename, pdf_sha256

# -------------------------
# Main script
# -------------------------
def main():
    conn = get_db_connection()
    cursor = conn.cursor()

# Get all accounts
    cursor.execute("SELECT * FROM bank_accounts;")
    accounts = query_to_dict(cursor)

# Get all transactions
    cursor.execute("SELECT * FROM bank_transactions;")
    transactions = query_to_dict(cursor)

    created_cases = []

    for txn in transactions:
        account = next((a for a in accounts if a["account_no"] == txn["account_no"]), None)
        if account:
            case_id, pdf_filename, pdf_sha256 = create_transaction_pdf(account, txn)
            
            # Insert into email_cases
            cursor.execute("""
                INSERT INTO email_cases (
                    case_id, from_addr, to_addr, subject, body_lang,
                    router, top_label, top_score, top_categories,
                    entities, status, pdf_sha256
                )
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'received',%s)
                RETURNING id;
            """, (
                case_id,
                "bank@bankindia.com",
                f"{account['customer_name'].replace(' ', '').lower()}@gmail.com",
                f"{txn['txn_type'].upper()} ₹{txn['amount']} in your account",
                "en",
                "transaction",
                None,  # top_label
                None,  # top_score
                "{}",  # top_categories
                "{}",  # entities
                pdf_sha256
            ))
            mail_id = cursor.fetchone()[0]
            created_cases.append(mail_id)

    conn.commit()
    cursor.close()
    conn.close()

    print(f"Created {len(created_cases)} transaction emails.")

if __name__ == "__main__":
    main()
