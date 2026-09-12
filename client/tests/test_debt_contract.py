import sys
import unittest
from datetime import date
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from db import invoice_repo, finance_repo
from utils import pdf_export


def balance(month=9, opening=120000000, closing=150000000):
    return dict(cakupan="folder_bulan", cabang_id=1, folder_id=month, tahun=2026,
                bulan=month, nama_folder=f"{month}/2026", hutang_bawaan=Decimal(opening),
                sisa_hutang=Decimal(closing), modal_pusat=Decimal(30000000),
                masuk_barang=Decimal(0), masuk_uang=Decimal(0))


class DebtContractTests(unittest.TestCase):
    def test_full_payload_preserves_original_invoice_bon(self):
        data = {"header": [1, "SEP", "2026-09-01", "2026-09-01", "30000000", 9, 1, None],
                "transaksi": [], "keuangan_folder": balance()}
        with patch.object(invoice_repo, "api_get", return_value=data):
            header, transactions, financial = invoice_repo.get_invoice_full(1, with_finance=True)
            self.assertEqual(len(invoice_repo.get_invoice_full(1)), 2)  # Legacy read signature.
        self.assertEqual(header[4], Decimal(30000000))
        self.assertEqual(financial["hutang_bawaan"], Decimal(120000000))
        self.assertEqual(financial["sisa_hutang"], Decimal(150000000))
        self.assertEqual(transactions, [])

    def test_old_backend_or_missing_balance_is_not_silently_zero(self):
        for data in (None, {}, {"cakupan": "folder_bulan"}):
            with self.subTest(data=data), self.assertRaises(ValueError):
                finance_repo.parse_balance(data)

    def test_wrong_folder_balance_rejected(self):
        data = {"header": [1, "SEP", "2026-09-01", "2026-09-01", 30, 9, 1, None],
                "transaksi": [], "keuangan_folder": {**balance(), "cabang_id": 2}}
        with patch.object(invoice_repo, "api_get", return_value=data), self.assertRaises(ValueError):
            invoice_repo.get_invoice_full(1, with_finance=True)

    def test_batch_balances_use_branch_scope(self):
        with patch.object(finance_repo, "api_get", return_value=[balance()]) as get:
            result = finance_repo.get_folder_balances(1)
        get.assert_called_once_with("/folders/saldo-hutang", params={"cabang_id": 1})
        self.assertEqual(result[9]["hutang_bawaan"], Decimal(120000000))

    def test_folder_pdf_uses_month_closing_not_invoice_sum(self):
        elements, _, _, debt = pdf_export._folder_section_elements(
            "September", [], pdf_export._styles["Heading2"], balance(),
        )
        self.assertEqual(debt, Decimal(150000000))
        text = " ".join(e.getPlainText() for e in elements if hasattr(e, "getPlainText"))
        self.assertIn("120.000.000", text)
        self.assertIn("150.000.000", text)

    def test_cabang_pdf_takes_latest_calendar_balance_not_sum_or_list_order(self):
        folders = [
            {"nama_folder": "September", "invoices_with_transaksi": [], "keuangan_folder": balance()},
            {"nama_folder": "Agustus", "invoices_with_transaksi": [], "keuangan_folder": balance(8, 0, 120000000)},
        ]
        with patch.object(pdf_export.SimpleDocTemplate, "build") as build:
            pdf_export.generate_cabang_pdf("Cabang A", folders)
        elements = build.call_args.args[0]
        summary = next(e.getPlainText() for e in elements if hasattr(e, "getPlainText") and "Sisa Hutang Bulan Terakhir" in e.getPlainText())
        self.assertIn("150.000.000", summary)
        self.assertNotIn("270.000.000", summary)

    def test_invoice_and_folder_pdf_require_balance_and_can_render(self):
        today = date(2026, 9, 1)
        header = (1, "SEP", today, today, Decimal(30000000), 9, 1, None)
        with self.assertRaises(ValueError):
            pdf_export.generate_invoice_pdf(header, [])
        self.assertTrue(pdf_export.generate_invoice_pdf(header, [], keuangan_folder=balance()).startswith(b"%PDF"))
        self.assertTrue(pdf_export.generate_folder_pdf("September", [], keuangan_folder=balance()).startswith(b"%PDF"))


if __name__ == "__main__":
    unittest.main()
