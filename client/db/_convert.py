"""
_convert.py — helper untuk mengubah data mentah JSON dari API (string,
float) kembali jadi tipe Python yang dulu dipakai views/*.py (date,
Decimal, datetime), supaya kode view TIDAK PERLU diubah sama sekali.
"""
from datetime import date, datetime
from decimal import Decimal


def to_date(value):
    if value is None:
        return None
    if isinstance(value, date):
        return value
    return date.fromisoformat(value)


def to_datetime(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value)


def to_decimal(value):
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))
