import asyncio
import sys
import unittest
from datetime import date
from decimal import Decimal
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch


CLIENT_DIR = Path(__file__).resolve().parents[1]
PROJECT_DIR = CLIENT_DIR.parent
sys.path.insert(0, str(PROJECT_DIR / "client"))

import flet as ft
from state import app_state
from views import kas_navigation_view as navigation
from views import pendapatan_pengeluaran_view as detail


class FakePage:
    def __init__(self, route):
        self.route = route
        self.theme_mode = ft.ThemeMode.LIGHT
        self.width = 1100
        self.height = 750
        self.platform = ft.PagePlatform.WINDOWS
        self.views = []
        self.services = []
        self.dialogs = []

    def update(self):
        pass

    def show_dialog(self, dialog):
        self.dialogs.append(dialog)

    def pop_dialog(self):
        return self.dialogs.pop()


def walk(control):
    yield control
    for attribute in ("controls", "actions", "cells", "rows", "columns"):
        children = getattr(control, attribute, None)
        if isinstance(children, (list, tuple)):
            for child in children:
                yield from walk(child)
    for attribute in ("content", "title", "label"):
        child = getattr(control, attribute, None)
        if child is not None and not isinstance(child, (str, int, float)):
            yield from walk(child)


def text_values(control):
    return "\n".join(
        str(item.value) for item in walk(control) if isinstance(item, ft.Text)
    )


def button(control, label):
    return next(
        item for item in walk(control)
        if getattr(item, "content", None) == label
        and getattr(item, "on_click", None) is not None
    )


def field(control, label):
    return next(item for item in walk(control) if getattr(item, "label", None) == label)


class KasNavigationTests(unittest.TestCase):
    def mock(self, target, name, **kwargs):
        patcher = patch.object(target, name, **kwargs)
        self.addCleanup(patcher.stop)
        return patcher.start()

    def setUp(self):
        from requests.sessions import Session
        self.mock(Session, "request", side_effect=AssertionError("HTTP nyata dilarang"))
        self.branches = self.mock(
            navigation, "get_active_cabang", return_value=[(1, "Toko Zebor"), (2, "Cabang B")]
        )
        self.periods = self.mock(
            navigation,
            "get_periode_kas",
            return_value=[
                dict(bulan=1, tahun=2099, jumlah_transaksi=3,
                     total_pendapatan=2000000, total_pengeluaran=750000,
                     saldo_bersih=1250000),
                dict(bulan=9, tahun=2026, jumlah_transaksi=1,
                     total_pendapatan=0, total_pengeluaran=200000000,
                     saldo_bersih=-200000000),
            ],
        )
        self.navigation = self.mock(navigation, "navigate")
        self.detail_navigation = self.mock(detail, "navigate")
        self.rows = self.mock(detail, "get_transaksi_kas", return_value=[])
        self.create = self.mock(detail, "add_transaksi_kas", return_value=91)
        self.update = self.mock(detail, "update_transaksi_kas")
        self.delete = self.mock(detail, "delete_transaksi_kas")
        self.pdf = self.mock(detail, "generate_pendapatan_pengeluaran_pdf")
        self.log = self.mock(detail, "log_activity")
        self.picker = Mock(save_file=AsyncMock(return_value="kas-proposal.pdf"))
        self.mock(detail, "get_file_picker", return_value=self.picker)
        self.page = FakePage(navigation.BASE_ROUTE)
        app_state.user = dict(id=1, username="mock", role="admin", cabang_id=1,
                              nama_cabang="Toko Zebor")
        self.addCleanup(app_state.logout)

    def build_detail(self, year=2026, month=9):
        self.page.route = f"{navigation.BASE_ROUTE}/cabang/1/{year}/{month}"
        return detail.build_view(
            self.page, cabang_id=1, bulan=month, tahun=year, nama_cabang="Toko Zebor"
        )

    def test_syntax_all_candidate_files(self):
        for source in (CLIENT_DIR / "main.py", CLIENT_DIR / "views/kas_navigation_view.py", CLIENT_DIR / "views/pendapatan_pengeluaran_view.py"):
            compile(source.read_text(encoding="utf-8"), str(source), "exec")

    def test_pusat_sees_branch_folders(self):
        app_state.user["cabang_id"] = None
        body = navigation.build_view(self.page)
        self.assertIn("Pilih cabang", text_values(body))
        self.assertIn("Cabang B", text_values(body))
        self.assertEqual(self.periods.call_count, 2)
        self.assertIn("Total folder", text_values(body))
        button(body, "Lihat kas cabang ini").on_click(None)
        self.navigation.assert_called_once_with(self.page, f"{navigation.BASE_ROUTE}/cabang/1")

    def test_branch_user_sees_periods_without_fetching_other_branches(self):
        app_state.user["role"] = "karyawan"
        body = navigation.build_view(self.page)
        self.assertIn("Januari 2099", text_values(body))
        self.assertIn("September 2026", text_values(body))
        self.branches.assert_not_called()
        self.periods.assert_called_once_with(1)
        button(body, "Buka folder").on_click(None)
        self.navigation.assert_called_once_with(self.page, f"{navigation.BASE_ROUTE}/cabang/1/2099/1")

    def test_pusat_can_open_other_branch(self):
        app_state.user["cabang_id"] = None
        self.page.route = f"{navigation.BASE_ROUTE}/cabang/2"
        body = navigation.build_view(self.page)
        self.assertIn("Kas - Cabang B", text_values(body))
        self.periods.assert_called_once_with(2)

    def test_other_branch_is_denied_before_fetch(self):
        self.page.route = f"{navigation.BASE_ROUTE}/cabang/2/2026/9"
        self.assertIn("Akses ditolak", text_values(navigation.build_view(self.page)))
        self.branches.assert_not_called()
        self.periods.assert_not_called()
        self.rows.assert_not_called()

    def test_bad_routes_and_periods_are_rejected(self):
        for suffix in ("/bad", "/cabang/no", "/cabang/1/2026", "/cabang/1/2026/13",
                       "/cabang/1/1999/1", "/cabang/1/2101/1", "/cabang/1/2026/9/extra"):
            with self.subTest(suffix=suffix):
                self.page.route = navigation.BASE_ROUTE + suffix
                body = navigation.build_view(self.page)
                self.assertTrue("tidak valid" in text_values(body))
        self.rows.assert_not_called()
        self.periods.assert_not_called()

    def test_period_without_entries_can_be_opened_without_writes(self):
        self.periods.return_value = []
        body = navigation.build_view(self.page)
        self.assertIn("Belum ada transaksi Kas", text_values(body))
        button(body, "Buka folder bulan").on_click(None)
        dialog = self.page.dialogs[-1]
        field(dialog, "Bulan").value = "2"
        field(dialog, "Tahun").value = "2028"
        button(dialog, "Buka & Mulai Input Transaksi").on_click(None)
        self.navigation.assert_called_once_with(self.page, f"{navigation.BASE_ROUTE}/cabang/1/2028/2")
        self.create.assert_not_called()
        self.update.assert_not_called()
        self.delete.assert_not_called()

    def test_invalid_picker_year_is_rejected(self):
        body = navigation.build_view(self.page)
        button(body, "Buka folder bulan").on_click(None)
        dialog = self.page.dialogs[-1]
        field(dialog, "Tahun").value = "9999"
        button(dialog, "Buka & Mulai Input Transaksi").on_click(None)
        self.navigation.assert_not_called()
        self.assertIn("2000–2100", field(dialog, "Tahun").error_text)

    def test_backend_error_does_not_masquerade_as_empty_periods(self):
        self.periods.side_effect = RuntimeError("Backend tidak terhubung")
        body = navigation.build_view(self.page)
        self.assertIn("gagal dimuat", text_values(body))
        self.assertIn("Backend tidak terhubung", text_values(body))
        self.assertNotIn("Belum ada transaksi", text_values(body))

    def test_logged_out_user_does_not_fetch_data(self):
        app_state.logout()
        self.assertIn("Sesi berakhir", text_values(navigation.build_view(self.page)))
        self.branches.assert_not_called()
        self.periods.assert_not_called()

    def test_detail_route_keeps_branch_and_month_scope(self):
        self.page.route = f"{navigation.BASE_ROUTE}/cabang/1/2026/9"
        body = navigation.build_view(self.page)
        self.assertIn("Detail Kas - Toko Zebor", text_values(body))
        self.assertEqual(self.rows.call_args.kwargs["cabang_id"], 1)
        self.assertEqual(self.rows.call_args.kwargs["bulan"], 9)
        self.assertEqual(self.rows.call_args.kwargs["start_date"], date(2026, 9, 1))
        self.assertEqual(self.rows.call_args.kwargs["end_date"], date(2026, 9, 30))
        next(control for control in walk(body) if getattr(control, "tooltip", None) == "Kembali ke folder bulan").on_click(None)
        self.detail_navigation.assert_called_once_with(self.page, f"{navigation.BASE_ROUTE}/cabang/1")

    def test_leap_february_and_december_boundaries(self):
        self.build_detail(2028, 2)
        self.assertEqual(self.rows.call_args.kwargs["end_date"], date(2028, 2, 29))
        self.build_detail(2100, 12)
        self.assertEqual(self.rows.call_args.kwargs["end_date"], date(2100, 12, 31))

    def test_reset_and_empty_filters_keep_scope(self):
        body = self.build_detail()
        field(body, "Dari Tanggal (YYYY-MM-DD)").value = ""
        field(body, "Sampai Tanggal (YYYY-MM-DD)").value = ""
        button(body, "Terapkan").on_click(None)
        self.assertEqual(self.rows.call_args.kwargs["start_date"], date(2026, 9, 1))
        self.assertEqual(self.rows.call_args.kwargs["end_date"], date(2026, 9, 30))
        button(body, "Reset Filter").on_click(None)
        self.assertEqual(field(body, "Dari Tanggal (YYYY-MM-DD)").value, "2026-09-01")
        self.assertEqual(self.rows.call_args.kwargs["bulan"], 9)

    def test_out_of_period_filter_is_rejected(self):
        body = self.build_detail()
        field(body, "Dari Tanggal (YYYY-MM-DD)").value = "2026-08-31"
        self.rows.reset_mock()
        button(body, "Terapkan").on_click(None)
        self.rows.assert_not_called()
        self.assertIn("September 2026", text_values(self.page.dialogs[-1]))

    def test_add_form_uses_selected_future_month(self):
        app_state.user["cabang_id"] = None
        body = self.build_detail(2099, 1)
        button(body, "Tambah Transaksi").on_click(None)
        dialog = self.page.dialogs[-1]
        self.assertEqual(field(dialog, "Tanggal (YYYY-MM-DD)").value, "2099-01-01")
        branch = field(dialog, "Cabang")
        self.assertTrue(branch.disabled)
        self.assertEqual(branch.value, "1")

    def test_add_outside_selected_month_is_rejected(self):
        body = self.build_detail()
        button(body, "Tambah Transaksi").on_click(None)
        dialog = self.page.dialogs[-1]
        field(dialog, "Tanggal (YYYY-MM-DD)").value = "2026-10-01"
        button(dialog, "Simpan").on_click(None)
        self.create.assert_not_called()
        self.assertIn("September 2026", text_values(self.page.dialogs[-1]))

    def test_save_uses_selected_branch(self):
        app_state.user["cabang_id"] = None
        body = self.build_detail()
        button(body, "Tambah Transaksi").on_click(None)
        dialog = self.page.dialogs[-1]
        field(dialog, "Tanggal (YYYY-MM-DD)").value = "2026-09-10"
        field(dialog, "Nominal (Rp) *").value = "150000"
        field(dialog, "Keterangan / Deskripsi").value = "Contoh pengujian mock"
        field(dialog, "Cabang").value = "2"
        button(dialog, "Simpan").on_click(None)
        self.create.assert_called_once()
        self.assertEqual(self.create.call_args.kwargs["cabang_id"], 1)
        self.assertEqual(self.create.call_args.kwargs["tanggal"], date(2026, 9, 10))

    def test_pdf_uses_selected_branch_and_month(self):
        self.rows.return_value = [dict(
            id=91, cabang_id=1, nama_cabang="Toko Zebor", tanggal=date(2026, 9, 10),
            jenis="Pendapatan", kategori="Lain-lain", nominal=Decimal("150000"),
            keterangan="Mock", nota=""
        )]
        body = self.build_detail()
        asyncio.run(button(body, "Export ke PDF").on_click(None))
        self.pdf.assert_called_once()
        info = self.pdf.call_args.args[1]
        self.assertEqual(info["cabang"], "Toko Zebor")
        self.assertEqual(info["periode"], "01-09-2026 s/d 30-09-2026")
        self.assertEqual(self.rows.call_args.kwargs["cabang_id"], 1)

    def test_incomplete_data_stays_blocked_for_pdf(self):
        self.rows.side_effect = RuntimeError("Data mencapai batas 500 transaksi")
        body = self.build_detail()
        self.assertIn("Tidak dapat memuat data transaksi", text_values(body))
        asyncio.run(button(body, "Export ke PDF").on_click(None))
        self.pdf.assert_not_called()
        self.assertIn("PDF tidak dibuat", text_values(self.page.dialogs[-1]))

    def test_mobile_dark_controls_can_be_constructed(self):
        self.page.width = 390
        self.page.height = 844
        self.page.theme_mode = ft.ThemeMode.DARK
        self.assertIn("Januari 2099", text_values(navigation.build_view(self.page)))
        body = self.build_detail()
        button(body, "Tambah").on_click(None)
        self.assertFalse(any(
            getattr(control, "label", None) == "Cabang"
            for control in walk(self.page.dialogs[-1])
        ))

    def test_branch_summaries_are_lazy_and_cached_per_page(self):
        app_state.user["cabang_id"] = None
        self.branches.return_value = [(branch_id, f"Cabang {branch_id}") for branch_id in range(1, 14)]
        body = navigation.build_view(self.page)
        self.assertEqual(self.periods.call_count, 10)
        next(control for control in walk(body) if getattr(control, "tooltip", None) == "Halaman berikutnya").on_click(None)
        self.assertEqual(self.periods.call_count, 13)
        next(control for control in walk(body) if getattr(control, "tooltip", None) == "Halaman sebelumnya").on_click(None)
        self.assertEqual(self.periods.call_count, 13)

    def test_branch_summary_error_is_not_zero(self):
        app_state.user["cabang_id"] = None
        self.periods.side_effect = RuntimeError("Backend unavailable")
        body = navigation.build_view(self.page)
        self.assertIn("Tidak tersedia", text_values(body))
        self.assertIn("Ringkasan gagal dimuat", text_values(body))
        self.assertNotIn("Rp 0", text_values(body))

    def test_period_refresh_updates_empty_state(self):
        body = navigation.build_view(self.page)
        empty = next(control for control in walk(body) if isinstance(control, ft.Text) and str(control.value).startswith("Belum ada transaksi Kas"))
        self.assertFalse(empty.visible)
        self.periods.return_value = []
        button(body, "Segarkan").on_click(None)
        self.assertTrue(empty.visible)

    def test_folder_styles_match_invoice_tokens(self):
        app_state.user["cabang_id"] = None
        body = navigation.build_view(self.page)
        cards = [control for control in walk(body) if isinstance(control, ft.Container) and control.col == {"xs": 12, "sm": 6, "md": 4}]
        self.assertEqual(len(cards), 2)
        self.assertTrue(all(card.padding == 20 and card.border_radius == 12 for card in cards))
        self.page.route = f"{navigation.BASE_ROUTE}/cabang/1"
        body = navigation.build_view(self.page)
        cards = [control for control in walk(body) if isinstance(control, ft.Container) and control.col == {"xs": 12, "sm": 6, "md": 4}]
        self.assertEqual(len(cards), 2)
        self.assertTrue(all(card.padding == 16 and card.border_radius == 12 for card in cards))


if __name__ == "__main__":
    unittest.main(verbosity=2)
