"""
utils/hutang_style.py — versi UI (butuh flet) dari logika di
utils/hutang_calc.py. Dipakai oleh views/*.py untuk pewarnaan card.
"""
import flet as ft
from utils.hutang_calc import hutang_amount


def hutang_style(sisa_hutang):
    """Kembalikan (nilai_absolut, warna_bg, warna_teks) untuk card Sisa Hutang.
    Merah kalau masih ada hutang, hijau kalau lunas/lebih bayar."""
    nilai, is_lunas = hutang_amount(sisa_hutang)
    if is_lunas:
        return nilai, ft.Colors.GREEN_50, ft.Colors.GREEN_900, ft.Colors.GREEN_900, ft.Colors.GREEN_50
    return nilai, ft.Colors.RED_50, ft.Colors.RED_900, ft.Colors.RED_900, ft.Colors.RED_50
