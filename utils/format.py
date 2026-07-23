MONTH_NAMES_ID = [
    "Januari", "Februari", "Maret", "April", "Mei", "Juni",
    "Juli", "Agustus", "September", "Oktober", "November", "Desember",
]

def format_rupiah(value: int) -> str:
    """1234567 -> 'Rp 1.234.567'"""
    return f"Rp {value:,.0f}".replace(",", ".")

def format_month_year(month: int, year:int) -> str:
    return f"{MONTH_NAMES_ID[month - 1]} {year}"