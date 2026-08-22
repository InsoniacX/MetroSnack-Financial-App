"""
Route auth. Ini perbaikan dari bug di auth_repo.py lama:
sebelumnya AccountLockedError di-raise LALU ketangkep balik oleh
`except Exception` generik di fungsi yang sama, jadi user tidak
pernah lihat pesan "akun terkunci" -- cuma dapat login gagal biasa.
Di sini exception ditangani dengan jelas dan pesan lockout betul-betul
sampai ke client (lewat HTTP 423 Locked).
"""
from fastapi import APIRouter, HTTPException, status
from datetime import datetime, timedelta
from database.connection import fetch_one, execute
from repositories.activity_repo import log_activity
from auth.security import verify_password, create_access_token
from models.schemas import LoginRequest, TokenResponse
from config import MAX_FAILED_ATTEMPTS, LOCKOUT_MINUTES

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest):
    row = fetch_one("""
        SELECT u.id, u.username, u.password_hash, u.nama_lengkap, u.role, u.aktif,
            u.failed_attempts, u.locked_until, u.cabang_id, c.nama_cabang
        FROM users u
        LEFT JOIN cabang c ON c.id = u.cabang_id
        WHERE u.username=%s
    """, (body.username,))

    if row is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Username atau password salah")

    uid, uname, phash, nama, role, aktif, failed_attempts, locked_until, cabang_id, nama_cabang = row

    if not aktif:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Akun tidak aktif")

    if locked_until and locked_until > datetime.now():
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail={"message": f"Akun terkunci sampai {locked_until.strftime('%H:%M')}",
                    "unlock_until": locked_until.isoformat()},
        )

    if not verify_password(body.password, phash):
        new_failed = (failed_attempts or 0) + 1
        if new_failed >= MAX_FAILED_ATTEMPTS:
            unlock_time = datetime.now() + timedelta(minutes=LOCKOUT_MINUTES)
            execute("UPDATE users SET failed_attempts=0, locked_until=%s WHERE id=%s", (unlock_time, uid))
            log_activity(uid, uname, "LOGIN", "auth", uid, f"Akun dikunci {LOCKOUT_MINUTES} menit karena {MAX_FAILED_ATTEMPTS}x salah password berturut-turut", cabang_id)
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail={"message": f"Akun terkunci sampai {unlock_time.strftime('%H:%M')}",
                        "unlock_until": unlock_time.isoformat()},
            )
        execute("UPDATE users SET failed_attempts=%s WHERE id=%s", (new_failed, uid))
        log_activity(uid, uname, "LOGIN", "auth", uid, f"Login gagal (percobaan ke-{new_failed} dari {MAX_FAILED_ATTEMPTS})", cabang_id)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Username atau password salah")

    # Login sukses
    if failed_attempts:
        execute("UPDATE users SET failed_attempts=0, locked_until=NULL WHERE id=%s", (uid,))
    log_activity(uid, uname, "LOGIN", "auth", uid, "Login berhasil", cabang_id)

    token = create_access_token({"sub": str(uid), "username": uname, "role": role, "cabang_id": cabang_id})
    return TokenResponse(access_token=token, id=uid, username=uname, role=role, nama=nama, cabang_id=cabang_id, nama_cabang=nama_cabang)
