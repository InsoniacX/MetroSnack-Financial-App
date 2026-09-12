"""Pure financial and HTTP contract tests: no real DB/login/seed required."""
from copy import deepcopy
from decimal import Decimal

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from auth.dependencies import get_current_user
from api import routes_folder, routes_invoice, routes_dashboard
from repositories import finance_repo, folder_repo, invoice_repo, transaksi_repo
from services.finance_service import hitung_riwayat_hutang, ringkasan_seluruh_cabang


def period(fid, month, modal=0, uang=0, barang=0, cid=1, year=2026, count=1):
    return dict(folder_id=fid, bulan=month, tahun=year, cabang_id=cid,
                nama_cabang=f"Cabang {cid}", nama_folder=f"{month}/{year}",
                total_invoice=count, modal_pusat=Decimal(str(modal)),
                masuk_uang=Decimal(str(uang)), masuk_barang=Decimal(str(barang)))


def test_august_september_october_carry_once():
    periods, branches = hitung_riwayat_hutang([
        period(3, 10, uang=10000000), period(1, 8, modal=120000000),
        period(2, 9, modal=30000000),
    ])
    assert [p["hutang_bawaan"] for p in periods] == [0, 120000000, 150000000]
    assert [p["sisa_hutang"] for p in periods] == [120000000, 150000000, 140000000]
    summary = ringkasan_seluruh_cabang(branches)
    assert summary["sisa_hutang"] == 140000000
    assert summary["modal_pusat"] == 150000000  # Not opening balance + new debt.


def test_correction_replays_all_following_periods_without_mutating_inputs():
    rows = [period(1, 8, modal=120000000), period(2, 9, modal=30000000), period(3, 10)]
    original = deepcopy(rows)
    before, _ = hitung_riwayat_hutang(rows)
    assert rows == original
    rows[0]["masuk_uang"] = Decimal("20000000")
    after, _ = hitung_riwayat_hutang(rows)
    assert before[1]["sisa_hutang"] == 150000000
    assert after[1]["hutang_bawaan"] == 100000000
    assert after[2]["sisa_hutang"] == 130000000


def test_backdated_folder_insertion_and_deletion_recalculate():
    august = period(1, 8, modal=120000000)
    october = period(3, 10, modal=10000000)
    assert hitung_riwayat_hutang([october, august])[0][-1]["sisa_hutang"] == 130000000
    september = period(99, 9, uang=20000000)
    assert hitung_riwayat_hutang([october, august, september])[0][-1]["sisa_hutang"] == 110000000
    assert hitung_riwayat_hutang([september, october])[0][-1]["sisa_hutang"] == 10000000


def test_empty_folder_and_year_boundary():
    periods, _ = hitung_riwayat_hutang([
        period(3, 2, modal=10, year=2027), period(2, 1, year=2027, count=0),
        period(1, 12, modal=120000000),
    ])
    assert periods[1]["sisa_hutang"] == 120000000
    assert periods[2]["sisa_hutang"] == 120000010


def test_payoff_overpayment_does_not_become_next_month_debt_or_credit():
    periods, _ = hitung_riwayat_hutang([
        period(1, 8, modal=120, uang=150), period(2, 9, modal=20), period(3, 10, uang=20),
    ])
    assert [p["hutang_bawaan"] for p in periods] == [0, 0, 20]
    assert [p["sisa_hutang"] for p in periods] == [0, 20, 0]


def test_branches_cannot_offset_each_other():
    periods, branches = hitung_riwayat_hutang([
        period(1, 8, modal=120, cid=1), period(2, 9, modal=30, cid=1),
        period(4, 9, uang=1000, cid=2),
    ])
    assert periods[-1]["hutang_bawaan"] == 0
    assert ringkasan_seluruh_cabang(branches)["sisa_hutang"] == 150


def test_multiple_invoices_aggregate_before_clamp():
    # September: invoice 1 pays 200; invoice 2 adds 150. One shared opening 120.
    periods, _ = hitung_riwayat_hutang([
        period(1, 8, modal=120), period(2, 9, modal=150, uang=200, count=2),
    ])
    assert periods[-1]["hutang_bawaan"] == 120
    assert periods[-1]["sisa_hutang"] == 70


def test_no_folders_and_decimal_precision():
    empty = period(None, None, year=None, count=0)
    periods, branches = hitung_riwayat_hutang([empty])
    assert periods == []
    assert branches[0]["sisa_hutang"] == 0
    assert ringkasan_seluruh_cabang([])["sisa_hutang"] == 0
    periods, _ = hitung_riwayat_hutang([period(1, 8, modal="0.10"), period(2, 9, modal="0.20")])
    assert periods[-1]["sisa_hutang"] == Decimal("0.30")


@pytest.fixture
def debt_api(monkeypatch):
    from database import connection
    monkeypatch.setattr(connection, "get_pool", lambda: pytest.fail("Real DB forbidden"))
    rows = [period(1, 8, modal=120000000), period(2, 9, modal=30000000), period(3, 10)]
    calls = []

    def totals(cid=None, through_folder_id=None, active_only=False):
        calls.append((cid, through_folder_id, active_only))
        selected = [r for r in rows if cid is None or r["cabang_id"] == cid]
        if through_folder_id is not None:
            target = next(r for r in rows if r["folder_id"] == through_folder_id)
            selected = [r for r in selected if (r["tahun"], r["bulan"]) <= (target["tahun"], target["bulan"])]
        return deepcopy(selected)

    monkeypatch.setattr(finance_repo, "get_monthly_totals", totals)
    monkeypatch.setattr(folder_repo, "get_folder_header", lambda fid: (fid, "September", 1, "Cabang 1") if fid == 2 else None)
    monkeypatch.setattr(invoice_repo, "get_invoice_header", lambda iid: (10, "TEST", None, None, Decimal(30000000), 2, 1, None) if iid == 10 else None)
    monkeypatch.setattr(invoice_repo, "get_invoice_totals", lambda iid: (Decimal(30000000), 0, 0))
    monkeypatch.setattr(transaksi_repo, "get_transaksi", lambda iid: [])
    app = FastAPI()
    for router in (routes_folder.router, routes_invoice.router, routes_dashboard.router):
        app.include_router(router)
    user = {"id": 1, "username": "test", "role": "admin", "cabang_id": 1}
    app.dependency_overrides[get_current_user] = lambda: user
    with TestClient(app) as client:
        yield client, rows, calls, user


def test_http_folder_invoice_dashboard_and_correction(debt_api):
    client, rows, calls, _ = debt_api
    for url in ("/folders/2/saldo-hutang", "/invoices/10/sisa-hutang"):
        response = client.get(url)
        assert response.status_code == 200, response.text
        assert response.json()["hutang_bawaan"] == 120000000
        assert response.json()["sisa_hutang"] == 150000000
    full = client.get("/invoices/10/full").json()
    assert full["header"][4] == 30000000  # Stored bon is never replaced by 150m.
    assert full["keuangan_folder"]["sisa_hutang"] == 150000000
    assert client.get("/dashboard/summary").json()["sisa_hutang"] == 150000000
    rows[0]["masuk_uang"] = Decimal(20000000)
    assert client.get("/invoices/10/full").json()["keuangan_folder"]["sisa_hutang"] == 130000000
    assert client.get("/dashboard/summary").json()["sisa_hutang"] == 130000000
    assert all(call[0] == 1 for call in calls)


def test_http_limit_applied_after_replay_and_list_route_not_shadowed(debt_api):
    client, _, _, _ = debt_api
    result = client.get("/dashboard/monthly-trend?limit_months=1").json()
    assert len(result) == 1
    assert result[0]["hutang_bawaan"] == 150000000
    assert len(client.get("/folders/saldo-hutang").json()) == 3


def test_http_denies_other_branch_before_financial_query(debt_api):
    client, _, calls, user = debt_api
    user["cabang_id"] = 2
    for url in ("/folders/2/saldo-hutang", "/invoices/10/full", "/invoices/10/sisa-hutang",
                "/folders/saldo-hutang?cabang_id=1", "/dashboard/summary?cabang_id=1"):
        assert client.get(url).status_code == 403
    assert calls == []


def test_http_pusat_and_missing_folder(debt_api):
    client, _, calls, user = debt_api
    user["cabang_id"] = None
    assert client.get("/folders/2/saldo-hutang").status_code == 200
    assert client.get("/dashboard/cabang-breakdown").status_code == 200
    assert calls[-1] == (None, None, True)
    assert client.get("/folders/999/saldo-hutang").status_code == 404
    assert client.get("/invoices/999/full").status_code == 404


def test_repository_uses_one_parameterized_batch_query(monkeypatch):
    captured = []
    monkeypatch.setattr(finance_repo, "fetch_all", lambda sql, params: captured.append((sql, params)) or [])
    finance_repo.get_monthly_totals(7, 99, True)
    assert len(captured) == 1
    sql, params = captured[0]
    assert params == (7, 99, 7)
    assert "GROUP BY f.id, i.id" in sql
    assert "c.aktif = TRUE" in sql
