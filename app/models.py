from .db import get_db_connection

CREATE_MAILS_TABLE = """
CREATE TABLE IF NOT EXISTS email_cases (
  id SERIAL PRIMARY KEY,
  case_id VARCHAR(128) UNIQUE NOT NULL,
  from_addr VARCHAR(320) NOT NULL,
  to_addr VARCHAR(320) NOT NULL,
  subject TEXT NOT NULL,
  body_lang VARCHAR(8),
  router VARCHAR(64) NOT NULL,
  top_label VARCHAR(64),
  top_score DOUBLE PRECISION,
  top_categories JSONB,
  entities JSONB,
  status case_status DEFAULT 'received' NOT NULL,
  pdf_sha256 VARCHAR(64),
  created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
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
