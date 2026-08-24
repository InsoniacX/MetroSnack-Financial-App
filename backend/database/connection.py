"""
Lapisan koneksi database. Sama gayanya dengan connection.py lama (execute /
fetch_all / fetch_one) supaya kode repository lama gampang dipindah, tapi
sekarang pakai connection pool (ThreadedConnectionPool) karena backend
API akan melayani banyak request bersamaan, tidak seperti client desktop
yang cuma 1 user per proses.
"""
import psycopg2
from psycopg2 import pool
from config import DB_CONFIG

_pool = None


def init_pool(minconn=1, maxconn=10):
    global _pool
    if _pool is None:
        _pool = psycopg2.pool.ThreadedConnectionPool(minconn, maxconn, **DB_CONFIG)
    return _pool


def get_pool():
    if _pool is None:
        return init_pool()
    return _pool


def execute(query, params=None, returning=False):
    conn = get_pool().getconn()
    try:
        with conn.cursor() as cur:
            cur.execute(query, params or ())
            result = None
            if returning:
                row = cur.fetchone()
                result = row[0] if row else None
            conn.commit()
            return result
    except Exception:
        conn.rollback()
        raise
    finally:
        get_pool().putconn(conn)


def fetch_all(query, params=None):
    conn = get_pool().getconn()
    try:
        with conn.cursor() as cur:
            cur.execute(query, params or ())
            return cur.fetchall()
    finally:
        get_pool().putconn(conn)


def fetch_one(query, params=None):
    conn = get_pool().getconn()
    try:
        with conn.cursor() as cur:
            cur.execute(query, params or ())
            return cur.fetchone()
    finally:
        get_pool().putconn(conn)
