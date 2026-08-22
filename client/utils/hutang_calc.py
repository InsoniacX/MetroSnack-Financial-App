def hutang_amount(sisa_hutang):
    """Kembalikan (nilai_absolut, is_lunas) untuk sisa_hutang (Decimal/number).
    is_lunas True kalau sisa_hutang <= 0 (lunas atau lebih bayar)."""
    nilai = float(sisa_hutang or 0)
    is_lunas = nilai <= 0
    return abs(nilai), is_lunas
