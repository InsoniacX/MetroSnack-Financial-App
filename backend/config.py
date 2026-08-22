"""
Konfigurasi backend MetroSnack.

Semua nilai sensitif (password DB, JWT secret) HARUS diisi lewat
environment variable / file .env, JANGAN di-hardcode di sini.
Ini yang membuat backend aman untuk dipakai bareng client mobile
(client tidak lagi menyimpan kredensial PostgreSQL sama sekali).
"""
import os
from dotenv import load_dotenv

load_dotenv()

# --- Database ---
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "5432")),
    "dbname": os.getenv("DB_NAME", "metrosnack"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", ""),
}

# --- JWT / Auth ---
JWT_SECRET = os.getenv("JWT_SECRET", "CHANGE_ME_BEFORE_PRODUCTION")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "480"))  # 8 jam kerja

# --- Lockout policy (dipindah dari auth_repo.py lama, perilaku sama) ---
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_MINUTES = 15

# --- App ---
APP_TITLE = "MetroSnack API"
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")
