from .db import get_db_connection

CREATE_MAILS_TABLE = """
CREATE TABLE IF NOT EXISTS mails (
    id SERIAL PRIMARY KEY,
    account_no BIGINT NOT NULL,
    sender VARCHAR(255) NOT NULL,
    receiver VARCHAR(255) NOT NULL,
    subject TEXT NOT NULL,
    body TEXT NOT NULL,
    category VARCHAR(50) NOT NULL,
    priority INT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);
"""

CREATE_AUTH_TABLE = """
CREATE TABLE IF NOT EXISTS auth_users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL
);
"""
