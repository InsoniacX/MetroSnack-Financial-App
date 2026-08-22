from .http_client import api_get
from ._convert import to_datetime


def log_activity(*args, **kwargs):
    """NO-OP di sisi client. Backend API sekarang OTOMATIS mencatat
    activity log di setiap endpoint create/update/delete (lihat
    repositories/activity_repo.py di backend, dipanggil dari tiap route).
    Fungsi ini dipertahankan (bukan dihapus) supaya semua pemanggilan
    log_activity(...) yang sudah ada di views/*.py TIDAK PERLU diubah --
    kalau fungsi ini diisi ulang jadi manggil API, log akan tercatat 2x."""
    pass


def get_recent_activities(cabang_id=None, limit=200):
    params = {"limit": limit}
    if cabang_id is not None:
        params["cabang_id"] = cabang_id
    rows = api_get("/activity-log", params=params)
    result = []
    for r in rows:
        aid, username, action, entity, entity_id, description, created_at, nama_cabang = r
        result.append((aid, username, action, entity, entity_id, description, to_datetime(created_at), nama_cabang))
    return result
