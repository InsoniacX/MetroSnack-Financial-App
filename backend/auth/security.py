"""
Utilitas keamanan: hash password (bcrypt, sama seperti kode lama) dan
pembuatan/verifikasi JWT untuk autentikasi API.
"""
import bcrypt
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from config import JWT_SECRET, JWT_ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode(), password_hash.encode())


def create_access_token(data: dict) -> str:
    """
    data harus berisi minimal: sub (user id), role, cabang_id.
    role & cabang_id ditaruh di token supaya setiap request bisa
    diverifikasi otorisasinya di server tanpa query tambahan
    (branch isolation - lihat auth/dependencies.py).
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except JWTError:
        return None
