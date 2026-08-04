import psycopg2
from config import DB_CONFIG

def get_connection():
    return psycopg2.connect(**DB_CONFIG)

def fetch_all(query, params=None):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(query, params or ())
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

def fetch_one(query, params=None):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(query, params or ())
    row = None
    cur.close()
    conn.close()
    return row

def execute(query, params=None, returning=False):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(query, params or ())
    result = None
    if returning:
        row = cur.fetchone()
        result = row[0] if row else None
    conn.commit()
    cur.close()
    conn.close()
    return result
