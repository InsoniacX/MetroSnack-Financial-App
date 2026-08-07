import bcrypt
from datetime import datetime, timedelta
from db.connection import fetch_one, execute
from db.activity_repo import log_activity

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_MINUTES = 15


class AccountLockedError(Exception):
    def __init__(self, unlock_time):
        self.unlock_time = unlock_time
        super().__init__(f"Akun terkunci sampai {unlock_time.strftime('%H:%M')}")


def authenticate_user(username, password):
    row = fetch_one(
        """
        SELECT u.id, u.username, u.password_hash, u.nama_lengkap, u.role, u.aktif, u.failed_attempts, u.locked_until, u.cabang_id, c.nama_cabang
        FROM users u
        LEFT JOIN cabang c ON c.id = u.cabang_id
        WHERE u.username=%s""",
        (username,),
    )
    if row is None:
        return None
    uid, uname, phash, nama, role, aktif, failed_attempts, locked_until, cabang_id, nama_cabang = row

    if not aktif:
        return None

    if locked_until and locked_until > datetime.now():
        raise AccountLockedError(locked_until)

    if bcrypt.checkpw(password.encode(), phash.encode()):
        if failed_attempts:
            execute("UPDATE users SET failed_attempts=0, locked_until=NULL WHERE id=%s", (uid,))
        return {
            "id": uid, "username": uname, "nama": nama, "role": role,
            "cabang_id": cabang_id, "nama_cabang": nama_cabang,
        }

    new_failed = (failed_attempts or 0) + 1
    if new_failed >= MAX_FAILED_ATTEMPTS:
        unlock_time = datetime.now() + timedelta(minutes=LOCKOUT_MINUTES)
        execute("UPDATE users SET failed_attempts=0, locked_until=%s WHERE id=%s", (unlock_time, uid))
        try:
            log_activity(uid, uname, "LOGIN", "auth", uid, f"Akun dikunci {LOCKOUT_MINUTES} menit karena {MAX_FAILED_ATTEMPTS}x salah password berturut-turut", cabang_id)
        except Exception:
            pass
        raise AccountLockedError(unlock_time)
    else:
        execute("UPDATE users SET failed_attempts=%s WHERE id=%s", (new_failed, uid))
        try:
            log_activity(uid, uname, "LOGIN", "auth", uid, f"Login gagal (percobaan ke-{new_failed} dari {MAX_FAILED_ATTEMPTS})", cabang_id)
        except Exception:
            pass

    return None