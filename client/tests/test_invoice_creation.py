import sys
import unittest
from datetime import date
from decimal import Decimal
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import flet as ft
from state import app_state
from db import invoice_repo
from views import invoices_view, folder_detail_view


class Page:
    width = 1100
    height = 850
    theme_mode = ft.ThemeMode.LIGHT
    platform = ft.PagePlatform.WINDOWS

    def __init__(self):
        self.views, self.services, self.dialogs = [], [], []

    def update(self):
        pass

    def show_dialog(self, dlg):
        self.dialogs.append(dlg)

    def pop_dialog(self):
        return self.dialogs.pop()


def walk(control):
    yield control
    for name in ("controls", "actions", "rows", "cells", "columns"):
        children = getattr(control, name, None)
        if isinstance(children, (list, tuple)):
            for child in children:
                yield from walk(child)
    content = getattr(control, "content", None)
    if isinstance(content, ft.Control):
        yield from walk(content)


def click(control, label):
    next(c for c in walk(control) if getattr(c, "content", None) == label).on_click(None)


class InvoiceCreationTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(patch("requests.sessions.Session.request", side_effect=AssertionError("Real HTTP forbidden")))
        self.enterContext(patch.object(app_state, "user", {"id": 7, "username": "test", "cabang_id": 1, "role": "admin"}))
        self.page = Page()
        self.enterContext(patch.object(invoices_view, "get_folders", return_value=[]))
        self.enterContext(patch.object(invoices_view, "get_cabang_name", return_value="A"))
        self.enterContext(patch.object(folder_detail_view, "get_folder_header", return_value=(2, "September", 1, "A")))
        self.invoices = self.enterContext(patch.object(folder_detail_view, "get_invoices", return_value=[]))
        self.enterContext(patch.object(folder_detail_view, "get_folder_balance", return_value={"hutang_bawaan": Decimal(120000000), "sisa_hutang": Decimal(120000000)}))
        self.create_folder = self.enterContext(patch.object(invoices_view, "create_folder", return_value=2))
        self.create = {}
        self.navigate = {}
        for module in (invoices_view, folder_detail_view):
            self.create[module] = self.enterContext(patch.object(module, "create_invoice", return_value=10))
            self.navigate[module] = self.enterContext(patch.object(module, "navigate"))
            self.enterContext(patch.object(module, "log_activity"))

    def fill_dates_and_name(self, dialog):
        fields = [c for c in walk(dialog) if isinstance(c, ft.TextField)]
        self.assertFalse(any("bon" in (c.label or "").lower() for c in fields))
        for field in fields:
            if field.label in ("No.", "No. Laporan"):
                field.value = "SEP"
            elif field.label == "Tahun":
                field.value = "2026"
            else:
                field.value = "2026-09-01"

    def test_new_folder_can_be_saved_without_bon(self):
        view = invoices_view.build_folder_list(self.page, 1, "/invoices", False)
        trigger = next(c for c in walk(view) if getattr(c, "on_click", None) and "folder" in str(getattr(c, "content", "")).lower() and "baru" in str(getattr(c, "content", "")).lower())
        trigger.on_click(None)
        dialog = self.page.dialogs[-1]
        self.fill_dates_and_name(dialog)
        next(c for c in walk(dialog) if isinstance(c, ft.Dropdown)).value = "9"
        click(dialog, "Simpan & Mulai Input Transaksi")
        self.create_folder.assert_called_once_with(9, 2026, 1, 7)
        self.create[invoices_view].assert_called_once_with(2, "SEP", date(2026, 9, 1), date(2026, 9, 1), 7)
        self.navigate[invoices_view].assert_called_once_with(self.page, "/invoice/10")

    def test_empty_folder_invoice_can_be_saved_without_bon(self):
        view = folder_detail_view.build_view(self.page, 2)
        click(view, "Buat laporan baru")
        dialog = self.page.dialogs[-1]
        self.fill_dates_and_name(dialog)
        click(dialog, "Simpan & lanjut isi transaksi")
        self.create[folder_detail_view].assert_called_once_with(2, "SEP", date(2026, 9, 1), date(2026, 9, 1), 7)

    def test_bon_edit_field_only_visible_for_existing_nonzero_bon(self):
        for bon in (Decimal(0), Decimal(120000000)):
            with self.subTest(bon=bon):
                self.invoices.return_value = [(10, "OLD", date(2026, 8, 1), date(2026, 8, 1), bon, Decimal(0), Decimal(0))]
                view = folder_detail_view.build_view(self.page, 2)
                next(c for c in walk(view) if getattr(c, "tooltip", None) == "Edit").on_click(None)
                field = next(c for c in walk(self.page.dialogs[-1]) if getattr(c, "label", None) == "Bon lama (Rp)")
                self.assertEqual(field.visible, bool(bon))
                self.assertEqual(Decimal(field.value), bon)

    def test_adapter_does_not_send_bon_in_create_payload(self):
        with patch.object(invoice_repo, "api_post", return_value={"id": 10}) as post:
            invoice_repo.create_invoice(2, "SEP", date(2026, 9, 1), date(2026, 9, 1), 7)
        self.assertNotIn("invoice_bon", post.call_args.args[1])


if __name__ == "__main__":
    unittest.main()
