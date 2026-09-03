import os
from pathlib import Path
from urllib.parse import urlsplit

from dotenv import load_dotenv


load_dotenv(Path(__file__).with_name(".env"), override=False)

DEFAULT_API_BASE_URL = "http://127.0.0.1:8080"

MONTH = [
    "",
    "Januari",
    "Februari",
    "Maret",
    "April",
    "Mei",
    "Juni",
    "Juli",
    "Agustus",
    "September",
    "Oktober",
    "November",
    "Desember",
]

APP_TITLE = "MetroSnack Financial App"


def get_api_base_url():
    value = os.getenv(
        "METROSNACK_API_BASE_URL",
        DEFAULT_API_BASE_URL,
    ).strip().rstrip("/")

    parsed = urlsplit(value)

    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ValueError(
            "METROSNACK_API_BASE_URL harus berupa URL lengkap, "
            "contoh: http://127.0.0.1:8080"
        )

    try:
        parsed.port
    except ValueError as exc:
        raise ValueError("Port backend tidak valid.") from exc

    return value


def get_api_timeout():
    raw_value = os.getenv("METROSNACK_API_TIMEOUT_SECONDS", "15")

    try:
        timeout = float(raw_value)
    except ValueError as exc:
        raise ValueError(
            "METROSNACK_API_TIMEOUT_SECONDS harus berupa angka."
        ) from exc

    if timeout <= 0:
        raise ValueError(
            "METROSNACK_API_TIMEOUT_SECONDS harus lebih besar dari nol."
        )

    return timeout


API_BASE_URL = get_api_base_url()
API_TIMEOUT_SECONDS = get_api_timeout()