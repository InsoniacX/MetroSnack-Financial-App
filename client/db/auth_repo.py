from datetime import datetime
from .http_client import api_post, ApiError


class AccountLockedError(Exception):
    def __init__(self, unlock_time):
        self.unlock_time = unlock_time
        super().__init__(f"Akun terkunci sampai {unlock_time.strftime('%H:%M')}")


def authenticate_user(username, password):
    try:
        resp = api_post("/auth/login", {"username": username, "password": password})
    except ApiError as e:
        if e.status_code == 423:
            unlock_until = e.detail.get("unlock_until") if isinstance(e.detail, dict) else None
            unlock_time = datetime.fromisoformat(unlock_until) if unlock_until else datetime.now()
            raise AccountLockedError(unlock_time)
        if e.status_code in (401, 403):
            return None
        raise

    return {
        "id": resp["id"],
        "username": resp["username"],
        "nama": resp.get("nama"),
        "role": resp["role"],
        "cabang_id": resp.get("cabang_id"),
        "nama_cabang": resp.get("nama_cabang"),
        # Token disimpan di sini juga (bukan cuma di variabel lokal),
        # supaya http_client.py bisa ambil dari app_state.user tanpa
        # perlu ubah state.py sama sekali.
        "access_token": resp["access_token"],
    }
