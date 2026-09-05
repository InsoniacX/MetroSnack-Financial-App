from datetime import datetime
from decimal import Decimal, InvalidOperation


def _parse_indonesian_decimal(label, value_str, decimal_places):
    """Ubah angka berformat Indonesia menjadi Decimal tanpa tebakan ambigu."""
    if value_str is None or str(value_str).strip() == "":
        raise ValueError(f"{label} wajib diisi.")

    text = str(value_str).strip()

    if text.startswith("-"):
        raise ValueError(f"{label} tidak boleh bernilai negatif.")

    if not text or any(character not in "0123456789.," for character in text):
        raise ValueError(
            f"{label} harus berupa angka. "
            "Gunakan format seperti 150000 atau 150.000,50."
        )

    if text.count(",") > 1:
        raise ValueError(
            f"{label} memiliki format angka yang tidak valid."
        )

    if "," in text:
        integer_part, fractional_part = text.split(",", 1)

        if decimal_places == 0 or not fractional_part:
            raise ValueError(
                f"{label} memiliki format angka yang tidak valid."
            )

        if (
            not fractional_part.isdigit()
            or len(fractional_part) > decimal_places
        ):
            raise ValueError(
                f"{label} maksimal memiliki {decimal_places} angka desimal."
            )
    elif text.count(".") == 1:
        possible_integer, possible_fraction = text.split(".", 1)
        is_backend_decimal = (
            possible_integer.isdigit()
            and possible_fraction.isdigit()
            and 1 <= len(possible_fraction) <= decimal_places
        )

        if is_backend_decimal:
            # Nilai Decimal dari API di-prefill sebagai contoh "125000.00".
            # Format ini diterima agar edit data lama tidak gagal.
            integer_part = possible_integer
            fractional_part = possible_fraction
        else:
            integer_part = text
            fractional_part = ""
    else:
        integer_part = text
        fractional_part = ""

    if "." in integer_part:
        groups = integer_part.split(".")
        thousands_format_valid = (
            groups[0].isdigit()
            and 1 <= len(groups[0]) <= 3
            and all(
                group.isdigit() and len(group) == 3
                for group in groups[1:]
            )
        )

        if not thousands_format_valid:
            raise ValueError(
                f"{label} memiliki pemisah ribuan yang tidak valid. "
                "Gunakan format seperti 150.000 atau 1.500.000."
            )

        integer_digits = "".join(groups)
    else:
        if not integer_part.isdigit():
            raise ValueError(
                f"{label} harus berupa angka yang valid."
            )
        integer_digits = integer_part

    normalized = integer_digits
    if fractional_part:
        normalized += f".{fractional_part}"

    try:
        return Decimal(normalized)
    except InvalidOperation as error:
        raise ValueError(
            f"{label} harus berupa angka yang valid."
        ) from error


def parse_positive_decimal(
    label,
    value_str,
    *,
    allow_zero=True,
    max_digits=15,
    decimal_places=2,
):
    """
    Validasi nominal non-negatif menggunakan format angka Indonesia.

    Contoh yang diterima: 150000, 150.000, dan 150.000,50.
    Gunakan ``allow_zero=False`` untuk field transaksi yang wajib lebih dari nol.
    """
    if decimal_places < 0 or max_digits <= decimal_places:
        raise ValueError("Konfigurasi batas digit nominal tidak valid.")

    value = _parse_indonesian_decimal(
        label,
        value_str,
        decimal_places,
    )

    if value < 0:
        raise ValueError(f"{label} tidak boleh bernilai negatif.")

    if value == 0 and not allow_zero:
        raise ValueError(f"{label} harus lebih besar dari 0.")

    integer_digits_limit = max_digits - decimal_places
    integer_part = format(value, "f").split(".", 1)[0].lstrip("0")
    integer_digits_count = len(integer_part) if integer_part else 1

    if integer_digits_count > integer_digits_limit:
        raise ValueError(
            f"{label} maksimal memiliki {integer_digits_limit} "
            "digit sebelum koma."
        )

    return value


def parse_date(label, value_str):
    """Konversi string YYYY-MM-DD ke objek date, wajib format benar."""
    if not value_str or not str(value_str).strip():
        raise ValueError(f"{label} wajib diisi.")
    try:
        return datetime.strptime(value_str.strip(), "%Y-%m-%d").date()
    except ValueError as error:
        raise ValueError(
            f"{label} harus berformat YYYY-MM-DD, contoh: 2026-07-08."
        ) from error


def parse_year(label, value_str):
    if not value_str or not str(value_str).strip().isdigit():
        raise ValueError(
            f"{label} harus berupa angka tahun, contoh: 2026."
        )
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
