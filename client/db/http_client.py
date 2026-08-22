import requests

try:
    from config import API_BASE_URL
except ImportError:
    try:
        from client.config import API_BASE_URL
    except ImportError:
        API_BASE_URL = "http://localhost:8000"

try:
    from state import app_state
except ImportError:
    from client.state import app_state

TIMEOUT_SECONDS = 15


class ApiError(Exception):

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


def api_get(path, params=None):
    resp = requests.get(f"{API_BASE_URL}{path}", headers=_headers(), params=params, timeout=TIMEOUT_SECONDS)
    return _handle(resp)


def api_post(path, json_body=None):
    resp = requests.post(f"{API_BASE_URL}{path}", headers=_headers(), json=json_body, timeout=TIMEOUT_SECONDS)
    return _handle(resp)


def api_put(path, json_body=None):
    resp = requests.put(f"{API_BASE_URL}{path}", headers=_headers(), json=json_body, timeout=TIMEOUT_SECONDS)
    return _handle(resp)


def api_patch(path, params=None):
    resp = requests.patch(f"{API_BASE_URL}{path}", headers=_headers(), params=params, timeout=TIMEOUT_SECONDS)
    return _handle(resp)


def api_delete(path):
    resp = requests.delete(f"{API_BASE_URL}{path}", headers=_headers(), timeout=TIMEOUT_SECONDS)
    return _handle(resp)
