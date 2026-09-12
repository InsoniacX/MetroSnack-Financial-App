"""
utils/hutang_calc.py — logika murni (TANPA dependency ke flet) untuk
Sisa Hutang: nilai nonnegatif + status lunas/belum. Dipakai oleh
utils/hutang_style.py (versi UI, nambah warna flet) DAN utils/pdf_export.py
(PDF generation tidak butuh tahu apa-apa soal Flet).
"""
from decimal import Decimal


def hutang_amount(sisa_hutang):
    """Kembalikan (nilai_tampil, is_lunas) dengan presisi Decimal.

    Hutang lunas atau lebih bayar ditampilkan sebagai nol, bukan nilai absolut.
    Nilai positif tetap menunjukkan hutang yang masih harus dibayar.
    """
    nilai = Decimal(str(sisa_hutang or 0))
    is_lunas = nilai <= 0
    return (Decimal("0") if is_lunas else nilai), is_lunas
