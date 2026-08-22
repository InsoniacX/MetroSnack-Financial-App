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

bearer_scheme = HTTPBearer()


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> dict:
    payload = decode_access_token(credentials.credentials)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token tidak valid atau kedaluwarsa",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return {
        "id": int(payload["sub"]),
        "username": payload.get("username"),
        "role": payload.get("role"),
        "cabang_id": payload.get("cabang_id"),
    }


def require_admin(user: dict = Depends(get_current_user)) -> dict:
    if user["role"] != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Hanya admin pusat yang boleh mengakses ini")
    return user


def assert_cabang_access(user: dict, cabang_id: int):
    """
    Panggil ini di setiap endpoint yang menerima cabang_id dari
    client (path/query param). admin pusat boleh akses semua cabang;
    user cabang HANYA boleh akses cabang_id miliknya sendiri.
    """
    if user["role"] == "admin":
        return
    if user["cabang_id"] != cabang_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Anda tidak punya akses ke data cabang ini",
        )
