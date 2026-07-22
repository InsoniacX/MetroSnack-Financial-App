import sqlite3
import hashlib
import secrets
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = APP_DIR / "data"
DB_PATH = DATA_DIR / "metrosnack.db"
SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"

def get_db_connection() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def initialize_database():
    conn = get_db_connection()
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        conn.executescript(f.read())
    conn.commit()
    conn.close()

def query_one(sql: str, params=()):
    conn = get_db_connection()
    try: 
        return conn.execute(sql, params).fetchone()
    finally:
        conn.close()

def execute(sql: str, params=()):
    conn = get_db_connection()
    try:
        cursor = conn.execute(sql, params)
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()

def hash_password(password: str, salt: str | None = None) -> tuple[str, str]:
    if salt is None:
        salt = secrets.token_hex(16)
    hashed = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000)
    return hashed.hex(), salt

def verify_password(password: str, stored_hash: str, stored_salt: str) -> bool:
    new_hash, _ = hash_password(password, stored_salt)
    return secrets.compare_digest(new_hash, stored_hash)