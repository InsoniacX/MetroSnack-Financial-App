from datetime import date
from decimal import Decimal
from unittest.mock import Mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api import routes_invoice
from auth.dependencies import get_current_user
from repositories import folder_repo, invoice_repo
from services.finance_service import hitung_riwayat_hutang


BODY = {"no_laporan": "SEP", "tanggal_dibuat": "2026-09-01", "tanggal_laporan": "2026-09-01"}


@pytest.fixture
def invoice_api(monkeypatch):
    from database import connection
    monkeypatch.setattr(connection, "get_pool", lambda: pytest.fail("Real DB forbidden"))
    user = {"id": 7, "username": "test", "role": "admin", "cabang_id": 1}
    header = [10, "OLD", None, None, Decimal("120000000"), 2, 1, None]
    create = Mock(return_value=10)
    update = Mock()
    monkeypatch.setattr(folder_repo, "get_folder_header", lambda fid: (2, "September", 1, "A"))
    monkeypatch.setattr(invoice_repo, "get_invoice_header", lambda iid: header)
    monkeypatch.setattr(invoice_repo, "create_invoice", create)
    monkeypatch.setattr(invoice_repo, "update_invoice", update)
    monkeypatch.setattr(routes_invoice, "log_activity", Mock())
    app = FastAPI()
    app.include_router(routes_invoice.router)
    app.dependency_overrides[get_current_user] = lambda: user
    with TestClient(app) as client:
        yield client, create, update, header, user


def test_create_without_bon(invoice_api):
    client, create, _, _, _ = invoice_api
    response = client.post("/folders/2/invoices", json=BODY)
    assert response.status_code == 200, response.text
    create.assert_called_once_with(2, "SEP", date(2026, 9, 1), date(2026, 9, 1), 7)


def test_create_zero_bon_from_older_client_still_accepted(invoice_api):
    assert invoice_api[0].post("/folders/2/invoices", json={**BODY, "invoice_bon": "0"}).status_code == 200


@pytest.mark.parametrize("bon", ["1", "-1", "120000000", "NaN"])
def test_create_nonzero_or_invalid_bon_rejected(invoice_api, bon):
    client, create, _, _, _ = invoice_api
    assert client.post("/folders/2/invoices", json={**BODY, "invoice_bon": bon}).status_code == 422
    create.assert_not_called()


def test_edit_metadata_preserves_legacy_bon_when_field_omitted(invoice_api):
    client, _, update, _, _ = invoice_api
    assert client.put("/invoices/10", json=BODY).status_code == 200
    assert update.call_args.args[-1] == Decimal("120000000")


def test_edit_cannot_add_bon_to_invoice_without_bon(invoice_api):
    client, _, update, header, _ = invoice_api
    header[4] = Decimal(0)
    assert client.put("/invoices/10", json={**BODY, "invoice_bon": "30000000"}).status_code == 422
    update.assert_not_called()
    assert client.put("/invoices/10", json=BODY).status_code == 200
    assert update.call_args.args[-1] == 0


def test_existing_nonzero_bon_remains_editable(invoice_api):
    client, _, update, _, _ = invoice_api
    assert client.put("/invoices/10", json={**BODY, "invoice_bon": "100000000"}).status_code == 200
    assert update.call_args.args[-1] == Decimal("100000000")


def test_cross_branch_cannot_create_or_edit(invoice_api):
    client, create, update, _, user = invoice_api
    user["cabang_id"] = 99
    assert client.post("/folders/2/invoices", json=BODY).status_code == 403
    assert client.put("/invoices/10", json=BODY).status_code == 403
    create.assert_not_called()
    update.assert_not_called()


def test_legacy_bon_carries_to_new_month_with_goods_only():
    def row(fid, month, bon, goods, cash):
        return dict(folder_id=fid, bulan=month, tahun=2026, cabang_id=1, nama_cabang="A",
                    nama_folder=str(month), modal_pusat=Decimal(bon), masuk_barang=Decimal(goods), masuk_uang=Decimal(cash))
    rows = [row(1, 8, "100000000", "20000000", "0"), row(2, 9, "0", "30000000", "10000000")]
    periods, _ = hitung_riwayat_hutang(rows)
    assert periods[0]["sisa_hutang"] == 120000000
    assert periods[1]["hutang_bawaan"] == 120000000
    assert periods[1]["modal_pusat"] == 0
    assert periods[1]["sisa_hutang"] == 140000000  # Goods 30m counted once, payment 10m.
    rows[1]["masuk_uang"] = Decimal("150000000")
    assert hitung_riwayat_hutang(rows)[0][1]["sisa_hutang"] == 0


def test_repository_insert_always_has_zero_bon(monkeypatch):
    execute = Mock(return_value=7)
    monkeypatch.setattr(invoice_repo, "execute", execute)
    assert invoice_repo.create_invoice(2, "SEP", date(2026, 9, 1), date(2026, 9, 1), 7) == 7
    sql, params = execute.call_args.args
    assert "VALUES (%s,%s,%s,%s,0,%s)" in sql
    assert len(params) == 5
