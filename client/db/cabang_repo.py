from .http_client import api_get, api_post, api_put, api_patch


def get_active_cabang():
    rows = api_get("/cabang", params={"active_only": True})
    return [(r[0], r[1]) for r in rows]


def get_all_cabang():
    rows = api_get("/cabang")
    return [tuple(r) for r in rows]


def get_cabang_name(cabang_id):
    rows = api_get("/cabang")
    for r in rows:
        if r[0] == cabang_id:
            return r[1]
    return None


def create_cabang(nama_cabang, alamat):
    resp = api_post("/cabang", {"nama_cabang": nama_cabang, "alamat": alamat})
    return resp["id"]


def update_cabang(cabang_id, nama_cabang, alamat):
    api_put(f"/cabang/{cabang_id}", {"nama_cabang": nama_cabang, "alamat": alamat})


def set_cabang_aktif(cabang_id, aktif):
    api_patch(f"/cabang/{cabang_id}/aktif", params={"aktif": aktif})


def cabang_name_exist(nama_cabang, exclude_id=None):
    params = {"nama": nama_cabang}
    if exclude_id:
        params["exclude_id"] = exclude_id
    resp = api_get("/cabang/name-exists", params=params)
    return resp["exists"]
