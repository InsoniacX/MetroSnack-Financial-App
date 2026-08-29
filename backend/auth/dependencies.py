"""
Dependency FastAPI untuk mengambil user yang sedang login dari token,
dan untuk menegakkan isolasi cabang (poin 11.5 dokumen konteks):
user dari Cabang A TIDAK BOLEH bisa mengambil data Cabang B walaupun
dia mengubah cabang_id di URL/parameter secara manual.

Pakai HTTPBearer (bukan OAuth2PasswordBearer) supaya tombol "Authorize"
di Swagger UI menampilkan kotak "tempel token" yang simpel, bukan form
username/password OAuth2 standar yang tidak cocok dengan endpoint
/auth/login kita (yang menerima JSON, bukan form-urlencoded).
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from auth.security import decode_access_token
from database.connection import fetch_one

bearer_scheme = HTTPBearer()


def _credentials_error(detail: str = "Token tidak valid atau kadaluarsa"):
    return HTTPException(
        status_code = status.HTTP_401_UNAUTHORIZED,
        detail = detail,
        headers={"WWW-Authenticate": "Bearer"},
    )

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> dict:
    payload = decode_access_token(credentials.credentials)

    if payload is None:
        raise _credentials_error()

    try:
        user_id = int(payload.get("sub"))
    except (TypeError, ValueError):
        raise _credentials_error()

    row = fetch_one(
        """
        SELECT id, username, role, cabang_id, aktif
        FROM users
        WHERE id = %s
        """,
        (user_id,),
    )

    if row is None:
        raise _credentials_error("User tidak ditemukan, silakan login kembali")

    uid, username, role, cabang_id, aktif = row

    if not aktif:
        raise _credentials_error("Akun tidak aktif, silakan login kembali")

    # Role dan cabang selalu diambil dari database, bukan dari claim JWT lama.
    return {
        "id": uid,
        "username": username,
        "role": role,
        "cabang_id": cabang_id,
    }


def require_admin(user: dict = Depends(get_current_user)) -> dict:
    if user["role"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Hanya admin pusat yang boleh mengakses ini",
        )
    return user


def assert_cabang_access(user: dict, cabang_id: int):
    if user["role"] == "admin":
        return

    if user["cabang_id"] != cabang_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Anda tidak punya akses ke data cabang ini",
        )