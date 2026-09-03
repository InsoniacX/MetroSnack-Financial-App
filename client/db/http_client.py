"""
http_client.py — lapisan dasar komunikasi ke backend API MetroSnack.
Semua modul db/*.py lain manggil lewat sini, supaya urusan header,
token, dan error handling terpusat di satu tempat.
"""
import requests

# URL dan timeout backend divalidasi melalui config.py.
from config import API_BASE_URL, API_TIMEOUT_SECONDS

# app_state dipakai untuk ambil access_token yang disimpan waktu login
# (lihat db/auth_repo.py -- token ditaruh sebagai key "access_token" di
# dict user yang sama yang disimpan app_state.login()).
from state import app_state

TIMEOUT_SECONDS = API_TIMEOUT_SECONDS
_SESSION = requests.Session()


class ApiError(Exception):
    """Dilempar kalau backend API mengembalikan status error (4xx/5xx).
    Dipakai seperti Exception biasa -- str(error) berisi pesan yang
    ramah untuk ditampilkan di SnackBar, konsisten dengan cara lama
    (views selalu tulis `except Exception as ex: ... f"{ex}"`)."""

    def __init__(self, status_code, detail):
        self.status_code = status_code
        self.detail = detail
        if isinstance(detail, dict):
            message = detail.get("message") or detail.get("detail") or str(detail)
        else:
            message = str(detail)
        super().__init__(message)


def _headers():
    headers = {"Content-Type": "application/json"}
    token = None
    try:
        if app_state.user:
            token = app_state.user.get("access_token")
    except Exception:
        token = None
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _handle(resp):
    if resp.status_code >= 400:
        try:
            body = resp.json()
            detail = body.get("detail", body)
        except Exception:
            detail = resp.text
        raise ApiError(resp.status_code, detail)
    if resp.status_code == 204 or not resp.content:
        return None
    return resp.json()


def _request(method, path, params=None, json_body=None):
    response = _SESSION.request(
        method=method,
        url=f"{API_BASE_URL}{path}",
        headers=_headers(),
        params=params,
        json=json_body,
        timeout=TIMEOUT_SECONDS,
    )
    return _handle(response)


def api_get(path, params=None):
    return _request("GET", path, params=params)


def api_post(path, json_body=None):
    return _request("POST", path, json_body=json_body)


def api_put(path, json_body=None):
    return _request("PUT", path, json_body=json_body)


def api_patch(path, params=None):
    return _request("PATCH", path, params=params)


def api_patch_json(path, json_body=None):
    return _request("PATCH", path, json_body=json_body)


def api_delete(path):
    return _request("DELETE", path)
