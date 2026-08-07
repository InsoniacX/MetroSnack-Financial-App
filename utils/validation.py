from datetime import datetime
from decimal import Decimal, InvalidOperation


def parse_positive_decimal(label, value_str):
    """Konversi string ke Decimal, wajib angka valid dan tidak negatif."""
    if value_str is None or str(value_str).strip() == "":
        return Decimal(0)
    try:
        value = Decimal(str(value_str).replace(",", "").strip())
    except InvalidOperation:
        raise ValueError(f"{label} harus berupa angka yang valid.")
    if value < 0:
        raise ValueError(f"{label} tidak boleh bernilai negatif.")
    return value


def parse_date(label, value_str):
    """Konversi string YYYY-MM-DD ke objek date, wajib format benar."""
    if not value_str or not str(value_str).strip():
        raise ValueError(f"{label} wajib diisi.")
    try:
        return datetime.strptime(value_str.strip(), "%Y-%m-%d").date()
    except ValueError:
        raise ValueError(f"{label} harus berformat YYYY-MM-DD, contoh: 2026-07-08.")


def parse_year(label, value_str):
    if not value_str or not str(value_str).strip().isdigit():
        raise ValueError(f"{label} harus berupa angka tahun, contoh: 2026.")
    year = int(value_str.strip())
    if year < 2000 or year > 2100:
        raise ValueError(f"{label} harus di antara 2000-2100.")
    return year


def require_text(label, value_str, min_length=1, max_length=None):
    text = (value_str or "").strip()
    if len(text) < min_length:
        raise ValueError(f"{label} wajib diisi.")
    if max_length and len(text) > max_length:
        raise ValueError(f"{label} maksimal {max_length} karakter.")
    return text


def require_password(value_str, min_length=6):
    pwd = value_str or ""
    if len(pwd) < min_length:
        raise ValueError(f"Password minimal {min_length} karakter.")
    return pwd