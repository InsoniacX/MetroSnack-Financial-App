from decimal import Decimal


def money(value):
    return Decimal(str(value))


def test_health(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_admin_pusat_boleh_melihat_cabang(
    client,
    pusat_headers,
):
    response = client.get(
        "/cabang",
        headers=pusat_headers,
    )

    assert response.status_code == 200
    assert len(response.json()) == 2


def test_admin_cabang_tidak_boleh_melihat_semua_cabang(
    client,
    admin_zebor_headers,
):
    response = client.get(
        "/cabang",
        headers=admin_zebor_headers,
    )

    assert response.status_code == 403


def test_karyawan_tidak_boleh_mengelola_user(
    client,
    karyawan_zebor_headers,
):
    response = client.get(
        "/users",
        headers=karyawan_zebor_headers,
    )

    assert response.status_code == 403


def test_isolasi_cabang_dashboard(
    client,
    admin_zebor_headers,
    seeded_ids,
):
    response = client.get(
        "/dashboard/summary",
        params={"cabang_id": seeded_ids["cabang_b"]},
        headers=admin_zebor_headers,
    )

    assert response.status_code == 403


def test_isolasi_invoice_antar_cabang(
    client,
    cabang_b_headers,
    seeded_ids,
):
    response = client.get(
        f"/invoices/{seeded_ids['invoice_zebor']}",
        headers=cabang_b_headers,
    )

    assert response.status_code == 403


def test_invoice_zebor_tepat_lunas(
    client,
    admin_zebor_headers,
    seeded_ids,
):
    response = client.get(
        f"/invoices/{seeded_ids['invoice_zebor']}/sisa-hutang",
        headers=admin_zebor_headers,
    )

    assert response.status_code == 200

    payload = response.json()

    assert money(payload["modal_pusat"]) == Decimal("1000000")
    assert money(payload["masuk_uang"]) == Decimal("1500000")
    assert money(payload["masuk_barang"]) == Decimal("500000")
    assert money(payload["sisa_hutang"]) == Decimal("0")


def test_dashboard_tidak_menggandakan_invoice_bon(
    client,
    admin_zebor_headers,
    seeded_ids,
):
    response = client.get(
        "/dashboard/summary",
        params={"cabang_id": seeded_ids["zebor"]},
        headers=admin_zebor_headers,
    )

    assert response.status_code == 200

    payload = response.json()

    assert money(payload["modal_pusat"]) == Decimal("1000000")
    assert money(payload["masuk_uang"]) == Decimal("1500000")
    assert money(payload["masuk_barang"]) == Decimal("500000")
    assert money(payload["sisa_hutang"]) == Decimal("0")


def test_dashboard_admin_pusat(
    client,
    pusat_headers,
):
    response = client.get(
        "/dashboard/summary",
        headers=pusat_headers,
    )

    assert response.status_code == 200

    payload = response.json()

    assert money(payload["modal_pusat"]) == Decimal("1800000")
    assert money(payload["masuk_uang"]) == Decimal("2000000")
    assert money(payload["masuk_barang"]) == Decimal("700000")
    assert money(payload["sisa_hutang"]) == Decimal("500000")


def test_ringkasan_pendapatan_pengeluaran_harian(
    client,
    admin_zebor_headers,
    seeded_ids,
):
    response = client.get(
        "/pendapatan-pengeluaran/summary/harian",
        params={
            "cabang_id": seeded_ids["zebor"],
            "tanggal": "2099-01-10",
        },
        headers=admin_zebor_headers,
    )

    assert response.status_code == 200

    payload = response.json()

    assert money(payload["total_pendapatan"]) == Decimal("2000000")
    assert money(payload["total_pengeluaran"]) == Decimal("500000")
    assert money(payload["pendapatan_bersih"]) == Decimal("1500000")


def test_ringkasan_pendapatan_pengeluaran_bulanan(
    client,
    admin_zebor_headers,
    seeded_ids,
):
    response = client.get(
        "/pendapatan-pengeluaran/summary/bulanan",
        params={
            "cabang_id": seeded_ids["zebor"],
            "bulan": 1,
            "tahun": 2099,
        },
        headers=admin_zebor_headers,
    )

    assert response.status_code == 200

    payload = response.json()

    assert money(payload["total_pendapatan"]) == Decimal("2000000")
    assert money(payload["total_pengeluaran"]) == Decimal("750000")
    assert money(payload["pendapatan_bersih"]) == Decimal("1250000")


def test_fitur_pendapatan_ditolak_untuk_cabang_lain(
    client,
    cabang_b_headers,
    seeded_ids,
):
    response = client.get(
        "/pendapatan-pengeluaran",
        params={"cabang_id": seeded_ids["cabang_b"]},
        headers=cabang_b_headers,
    )

    assert response.status_code == 403


def test_tanggal_filter_terbalik_ditolak(
    client,
    admin_zebor_headers,
    seeded_ids,
):
    response = client.get(
        "/pendapatan-pengeluaran",
        params={
            "cabang_id": seeded_ids["zebor"],
            "tanggal_awal": "2099-01-20",
            "tanggal_akhir": "2099-01-01",
        },
        headers=admin_zebor_headers,
    )

    assert response.status_code == 422


def test_transaksi_negatif_ditolak(
    client,
    admin_zebor_headers,
    seeded_ids,
):
    response = client.post(
        f"/invoices/{seeded_ids['invoice_zebor']}/transaksi",
        headers=admin_zebor_headers,
        json={
            "tanggal": "2099-01-25",
            "masuk_barang": "-1",
            "masuk_uang": "0",
            "nota": "Harus ditolak",
        },
    )

    assert response.status_code == 422

def test_cors_preflight(client):
    response = client.options(
        "/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert "access-control-allow-origin" in response.headers