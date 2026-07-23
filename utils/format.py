def format_rupiah(value: int) -> str:
    """1234567 -> 'Rp 1.234.567'"""
    return f"Rp {value:,.0f}".replace(",", ".")