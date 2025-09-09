import random
from datetime import datetime
from .db import get_db_connection

# Transaction mail template
INSERT_MAIL = """
    INSERT INTO mails (account_no, txn_id, sender, receiver, subject, body, priority, category)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    RETURNING id;
"""

# -------------------------
# Transaction-based mail
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

    receiver = account['customer_name'].replace(" ", "").lower() + "@example.com"

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(INSERT_MAIL, (
        account["account_no"],
        txn["txn_id"],
        "bank@bankindia.com",
        receiver,
        subject,
        body.strip(),
        5,              # high priority
        'inbox'         # category
    ))
    mail_id = cursor.fetchone()[0]
    conn.commit()
    cursor.close()
    conn.close()
    return mail_id

# -------------------------
# Promotional mails
# -------------------------
PROMO_CATEGORIES = [
    {"subject": "Fixed Deposit Offer", "priority": 4, "category": "promotions"},
    {"subject": "Home Loan Offer", "priority": 3, "category": "promotions"},
    {"subject": "Car Loan Offer", "priority": 3, "category": "promotions"},
]

def generate_promotional_mail(account):
    promo = random.choice(PROMO_CATEGORIES)
    subject = promo["subject"]
    priority = promo["priority"]
    category = promo["category"]
    receiver = account['customer_name'].replace(" ", "").lower() + "@example.com"

    body = f"""
    Dear {account['customer_name']},

    We have a special offer for you: {subject}.

    Please contact your branch for more details.

    Regards,
    Bank India
    """

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO mails (account_no, sender, receiver, subject, body, priority, category)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING id;
    """, (
        account["account_no"],
        "bank@bankindia.com",
        receiver,
        subject,
        body.strip(),
        priority,
        category
    ))
    mail_id = cursor.fetchone()[0]
    conn.commit()
    cursor.close()
    conn.close()
    return mail_id
