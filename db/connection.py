import psycopg2
from config import DB_CONFIG

def get_connection():
    return psycopg2.connect(**DB_CONFIG)

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

def fetch_all(query, params=None):
    conn = get_connection()

    try:
        with conn.cursor() as cur:
            cur.execute(query, params or ())
            return cur.fetchall()
    finally:
        conn.close()

def fetch_one(query, params=None):
    conn = get_connection()

    try:
        with conn.cursor() as cur:
            cur.execute(query, params or ())
            return cur.fetchone()
    finally:
        conn.close()

