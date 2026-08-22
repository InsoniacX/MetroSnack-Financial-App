from .http_client import api_get, api_post, api_put, api_patch, api_delete


def get_all_users(cabang_id=None):
    params = {}
    if cabang_id is not None:
        params["cabang_id"] = cabang_id
    rows = api_get("/users", params=params)
    return [tuple(r) for r in rows]


def username_exists(username):
    resp = api_get("/users/username-exists", params={"username": username})
    return resp["exists"]


def create_user(username, password, nama_lengkap, role, cabang_id):
    resp = api_post("/users", {
        "username": username, "password": password, "nama_lengkap": nama_lengkap,
        "role": role, "cabang_id": cabang_id,
    })
    return resp["id"]


def update_user(user_id, nama_lengkap, role):
    api_put(f"/users/{user_id}", {"nama_lengkap": nama_lengkap, "role": role})


def get_user_cabang(user_id):
    rows = api_get("/users")
    for r in rows:
        if r[0] == user_id:
            return r[5]
    return None


def reset_password(user_id, new_password):
    api_post(f"/users/{user_id}/reset-password", {"new_password": new_password})


def set_aktif(user_id, aktif):
    api_patch(f"/users/{user_id}/aktif", params={"aktif": aktif})


def delete_user(user_id):
    api_delete(f"/users/{user_id}")
