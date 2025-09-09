import psycopg2

DATABASE_URL = "dbname=surferdev user=postgres password=your_password host=localhost port=5432"

def get_db_connection():
    conn = psycopg2.connect(DATABASE_URL)
    return conn

def query_to_dict(cursor):
    columns = [desc[0] for desc in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]
