import sys
import unittest
from datetime import date
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import flet as ft
from state import app_state
from utils.formatting import rp
from utils.hutang_calc import hutang_amount
from utils.hutang_style import hutang_style
from views import dashboard_view, invoice_detail_view


class HutangAmountTests(unittest.TestCase):
    def test_lunas_dan_lebih_bayar_tampil_nol(self):
        for value in (None, 0, Decimal("0"), -100000, Decimal("-100000.25"), "-100000"):
            with self.subTest(value=value):
                amount, is_lunas = hutang_amount(value)
                self.assertEqual(amount, Decimal("0"))
                self.assertTrue(is_lunas)
                self.assertEqual(rp(amount), "Rp 0")

    def test_hutang_positif_tidak_diubah(self):
        for value in (300000, Decimal("300000.25"), "300000.25"):
            with self.subTest(value=value):
                amount, is_lunas = hutang_amount(value)
                self.assertEqual(amount, Decimal(str(value)))
                self.assertFalse(is_lunas)
                self.assertEqual(rp(amount), "Rp 300.000")

    def test_presisi_decimal_dipertahankan(self):
        value = Decimal("123456789012345.67")
        amount, is_lunas = hutang_amount(value)
        self.assertIsInstance(amount, Decimal)
        self.assertEqual(amount, value)
        self.assertFalse(is_lunas)

    def test_warna_lunas_dan_lebih_bayar_hijau(self):
        for value in (0, -100000):
            with self.subTest(value=value):
                self.assertEqual(
                    hutang_style(value),
                    (Decimal("0"), ft.Colors.GREEN_50, ft.Colors.GREEN_900,
                     ft.Colors.GREEN_900, ft.Colors.GREEN_50),
                )

    def test_warna_hutang_positif_merah(self):
        self.assertEqual(
            hutang_style(300000),
            (Decimal("300000"), ft.Colors.RED_50, ft.Colors.RED_900,
             ft.Colors.RED_900, ft.Colors.RED_50),
        )


class HutangCardTests(unittest.TestCase):
    """Build real card controls with fake data; never contact an API/database."""

    def setUp(self):
        self.enterContext(patch(
            "requests.sessions.Session.request",
            side_effect=AssertionError("HTTP nyata dilarang dalam test"),
        ))
        self.enterContext(patch.object(app_state, "user", {
            "id": 1, "username": "test", "cabang_id": 1, "nama_cabang": "Zebor",
        }))
        self.page = SimpleNamespace(
            width=1100, height=750, theme_mode=ft.ThemeMode.LIGHT,
            platform=ft.PagePlatform.WINDOWS, views=[], services=[],
        )

    def assert_card(self, view_module, builder, label, expected, color):
        cards = {}
        original = view_module.metric_card

        def capture(page, title, value, *args, **kwargs):
            card = original(page, title, value, *args, **kwargs)
            cards[title] = card
            return card

        with patch.object(view_module, "metric_card", side_effect=capture):
            builder()
        self.assertEqual(cards[label].content.controls[1].value, expected)
        self.assertEqual(cards[label].bgcolor, color)

    def check_invoice(self, masuk_uang, expected, color):
        today = date(2026, 9, 1)
        header = (1, "INV-TEST", today, today, Decimal("1000000"), 1, 1, None)
        transaksi = [(1, today, Decimal("500000"), Decimal(masuk_uang),
                      Decimal(masuk_uang) - Decimal("500000"), "Lebih Uang", None)]
        balance = {"hutang_bawaan": Decimal(0),
                   "sisa_hutang": max(Decimal("1500000") - Decimal(masuk_uang), Decimal(0))}
        with patch.object(invoice_detail_view, "get_invoice_full", return_value=(header, transaksi, balance)):
            self.assert_card(
                invoice_detail_view, lambda: invoice_detail_view.build_view(self.page, 1),
                "Sisa Hutang Toko", expected, color,
            )

    def check_dashboard(self, sisa_hutang, expected, color):
        summary = {"omzet": 0, "barang": 0, "laba_bersih": 0, "sisa_hutang": sisa_hutang}
        with patch.object(dashboard_view, "get_dashboard_summary", return_value=summary), \
             patch.object(dashboard_view, "get_monthly_trend", return_value=[]):
            self.assert_card(
                dashboard_view, lambda: dashboard_view.build_view(self.page),
                "Total Hutang Toko Ini", expected, color,
            )

    def test_invoice_lunas(self):
        self.check_invoice("1500000", "Rp 0", ft.Colors.GREEN_50)

    def test_invoice_lebih_bayar(self):
        self.check_invoice("1600000", "Rp 0", ft.Colors.GREEN_50)

    def test_invoice_belum_lunas(self):
        self.check_invoice("1200000", "Rp 300.000", ft.Colors.RED_50)

    def test_invoice_uses_backend_carry_not_local_formula(self):
        today = date(2026, 9, 1)
        header = (1, "INV-SEP", today, today, Decimal("30000000"), 2, 1, None)
        balance = {"hutang_bawaan": Decimal("120000000"), "sisa_hutang": Decimal("150000000")}
        with patch.object(invoice_detail_view, "get_invoice_full", return_value=(header, [], balance)) as fetch:
            self.assert_card(
                invoice_detail_view, lambda: invoice_detail_view.build_view(self.page, 1),
                "Sisa Hutang Toko", "Rp 150.000.000", ft.Colors.RED_50,
            )
        fetch.assert_called_once_with(1, with_finance=True)

    def test_invoice_balance_error_does_not_render_zero_card(self):
        with patch.object(invoice_detail_view, "get_invoice_full", side_effect=ValueError("Saldo tidak lengkap")), \
             patch.object(invoice_detail_view, "metric_card") as card:
            view = invoice_detail_view.build_view(self.page, 1)
        card.assert_not_called()
        self.assertIn("gagal dimuat", view.controls[0].value)

    def test_dashboard_lunas(self):
        self.check_dashboard(0, "Rp 0", ft.Colors.GREEN_50)

    def test_dashboard_lebih_bayar(self):
        self.check_dashboard(-100000, "Rp 0", ft.Colors.GREEN_50)

    def test_dashboard_belum_lunas(self):
        self.check_dashboard(300000, "Rp 300.000", ft.Colors.RED_50)


if __name__ == "__main__":
    unittest.main()
