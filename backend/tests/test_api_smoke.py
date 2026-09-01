from decimal import Decimal
from uuid import uuid4
import pytest

from database.connection import execute


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


def test_daftar_supir_kenek_cabang_sendiri(
    client,
    admin_zebor_headers,
    seeded_ids,
):
    response = client.get(
        "/supir-kenek",
        params={"cabang_id": seeded_ids["zebor"]},
        headers=admin_zebor_headers,
    )

    assert response.status_code == 200

    names = {row[2] for row in response.json()}

    assert "Supir Test" in names
    assert "Kenek Test" in names


def test_isolasi_cabang_supir_kenek(
    client,
    admin_zebor_headers,
    seeded_ids,
):
    response = client.get(
        "/supir-kenek",
        params={"cabang_id": seeded_ids["cabang_b"]},
        headers=admin_zebor_headers,
    )

    assert response.status_code == 403


def test_karyawan_tidak_boleh_menambah_supir_kenek(
    client,
    karyawan_zebor_headers,
    seeded_ids,
):
    response = client.post(
        "/supir-kenek",
        headers=karyawan_zebor_headers,
        json={
            "cabang_id": seeded_ids["zebor"],
            "nama": "Tidak Boleh Dibuat",
        },
    )

    assert response.status_code == 403


def test_admin_dapat_mengelola_supir_kenek(
    client,
    admin_zebor_headers,
    seeded_ids,
):
    unique_suffix = uuid4().hex[:8]
    nama_awal = f"Supir API {unique_suffix}"
    nama_baru = f"Supir Update {unique_suffix}"
    created_id = None

    try:
        create_response = client.post(
            "/supir-kenek",
            headers=admin_zebor_headers,
            json={
                "cabang_id": seeded_ids["zebor"],
                "nama": nama_awal,
            },
        )

        assert create_response.status_code == 200
        created_id = create_response.json()["id"]

        duplicate_response = client.post(
            "/supir-kenek",
            headers=admin_zebor_headers,
            json={
                "cabang_id": seeded_ids["zebor"],
                "nama": nama_awal.lower(),
            },
        )

        assert duplicate_response.status_code == 409

        update_response = client.put(
            f"/supir-kenek/{created_id}",
            headers=admin_zebor_headers,
            json={"nama": nama_baru},
        )

        assert update_response.status_code == 200
        assert update_response.json() == {"ok": True}

        deactivate_response = client.patch(
            f"/supir-kenek/{created_id}/aktif",
            params={"aktif": False},
            headers=admin_zebor_headers,
        )

        assert deactivate_response.status_code == 200

        inactive_list_response = client.get(
            "/supir-kenek",
            params={
                "cabang_id": seeded_ids["zebor"],
                "active_only": False,
            },
            headers=admin_zebor_headers,
        )

        assert inactive_list_response.status_code == 200

        created_row = next(
            row
            for row in inactive_list_response.json()
            if row[0] == created_id
        )

        assert created_row[2] == nama_baru
        assert created_row[3] is False

        active_list_response = client.get(
            "/supir-kenek",
            params={"cabang_id": seeded_ids["zebor"]},
            headers=admin_zebor_headers,
        )

        active_ids = {
            row[0]
            for row in active_list_response.json()
        }

        assert created_id not in active_ids

    finally:
        if created_id is not None:
            execute(
                """
                DELETE FROM activity_log
                WHERE entity = %s AND entity_id = %s
                """,
                ("supir_kenek", created_id),
            )
            execute(
                "DELETE FROM supir_kenek WHERE id = %s",
                (created_id,),
            )


def get_seeded_supir_kenek_ids(
    client,
    headers,
    cabang_id,
):
    response = client.get(
        "/supir-kenek",
        params={"cabang_id": cabang_id},
        headers=headers,
    )

    assert response.status_code == 200

    roster = {
        row[2]: row[0]
        for row in response.json()
    }

    return roster["Supir Test"], roster["Kenek Test"]


def test_ringkasan_operasional_mobil_seed(
    client,
    admin_zebor_headers,
    seeded_ids,
):
    response = client.get(
        "/operasional-mobil/summary",
        params={"cabang_id": seeded_ids["zebor"]},
        headers=admin_zebor_headers,
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload["total_trip"] == 1
    assert money(payload["total_uang_jalan"]) == Decimal("150000")


def test_isolasi_cabang_operasional_mobil(
    client,
    admin_zebor_headers,
    seeded_ids,
):
    response = client.get(
        "/operasional-mobil",
        params={"cabang_id": seeded_ids["cabang_b"]},
        headers=admin_zebor_headers,
    )

    assert response.status_code == 403


def test_rentang_tanggal_operasional_terbalik_ditolak(
    client,
    admin_zebor_headers,
    seeded_ids,
):
    response = client.get(
        "/operasional-mobil",
        params={
            "cabang_id": seeded_ids["zebor"],
            "tanggal_awal": "2099-02-01",
            "tanggal_akhir": "2099-01-01",
        },
        headers=admin_zebor_headers,
    )

    assert response.status_code == 422


def test_supir_dan_kenek_yang_sama_ditolak(
    client,
    admin_zebor_headers,
    seeded_ids,
):
    supir_id, _ = get_seeded_supir_kenek_ids(
        client,
        admin_zebor_headers,
        seeded_ids["zebor"],
    )

    response = client.post(
        "/operasional-mobil",
        headers=admin_zebor_headers,
        json={
            "cabang_id": seeded_ids["zebor"],
            "tanggal": "2099-02-05",
            "supir_id": supir_id,
            "kenek_id": supir_id,
            "uang_jalan": "225000",
            "keterangan": "Harus ditolak",
        },
    )

    assert response.status_code == 422


def test_karyawan_dapat_mengelola_operasional_mobil(
    client,
    karyawan_zebor_headers,
    seeded_ids,
):
    supir_id, kenek_id = get_seeded_supir_kenek_ids(
        client,
        karyawan_zebor_headers,
        seeded_ids["zebor"],
    )
    created_id = None

    try:
        create_response = client.post(
            "/operasional-mobil",
            headers=karyawan_zebor_headers,
            json={
                "cabang_id": seeded_ids["zebor"],
                "tanggal": "2099-02-05",
                "supir_id": supir_id,
                "kenek_id": kenek_id,
                "uang_jalan": "225000",
                "keterangan": "  Operasional API Test  ",
            },
        )

        assert create_response.status_code == 200
        created_id = create_response.json()["id"]

        list_response = client.get(
            "/operasional-mobil",
            params={
                "cabang_id": seeded_ids["zebor"],
                "tanggal_awal": "2099-02-05",
                "tanggal_akhir": "2099-02-05",
            },
            headers=karyawan_zebor_headers,
        )

        assert list_response.status_code == 200

        created_row = next(
            row
            for row in list_response.json()
            if row[0] == created_id
        )

        assert money(created_row[7]) == Decimal("225000")
        assert created_row[8] == "Operasional API Test"

        update_response = client.put(
            f"/operasional-mobil/{created_id}",
            headers=karyawan_zebor_headers,
            json={
                "tanggal": "2099-02-05",
                "supir_id": supir_id,
                "kenek_id": kenek_id,
                "uang_jalan": "275000",
                "keterangan": "Operasional diperbarui",
            },
        )

        assert update_response.status_code == 200
        assert update_response.json() == {"ok": True}

        summary_response = client.get(
            "/operasional-mobil/summary",
            params={
                "cabang_id": seeded_ids["zebor"],
                "tanggal_awal": "2099-02-05",
                "tanggal_akhir": "2099-02-05",
            },
            headers=karyawan_zebor_headers,
        )

        assert summary_response.status_code == 200

        summary = summary_response.json()

        assert summary["total_trip"] == 1
        assert money(summary["total_uang_jalan"]) == Decimal("275000")

        delete_response = client.delete(
            f"/operasional-mobil/{created_id}",
            headers=karyawan_zebor_headers,
        )

        assert delete_response.status_code == 200
        assert delete_response.json() == {"ok": True}

    finally:
        if created_id is not None:
            execute(
                """
                DELETE FROM activity_log
                WHERE entity = %s AND entity_id = %s
                """,
                ("operasional_mobil", created_id),
            )
            execute(
                """
                DELETE FROM operasional_mobil
                WHERE id = %s
                """,
                (created_id,),
            )

@pytest.mark.parametrize(
    ("sumber", "expected_total"),
    [
        ("pabrik", Decimal("1000000")),
        ("balaraja", Decimal("750000")),
    ],
)
def test_ringkasan_pengambilan_kas_seed(
    client,
    admin_zebor_headers,
    seeded_ids,
    sumber,
    expected_total,
):
    response = client.get(
        f"/pengambilan-kas/{sumber}/summary",
        params={"cabang_id": seeded_ids["zebor"]},
        headers=admin_zebor_headers,
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload["sumber"] == sumber
    assert payload["total_data"] == 1
    assert money(payload["total_nominal"]) == expected_total


def test_sumber_pengambilan_kas_tidak_valid_ditolak(
    client,
    admin_zebor_headers,
    seeded_ids,
):
    response = client.get(
        "/pengambilan-kas/gudang",
        params={"cabang_id": seeded_ids["zebor"]},
        headers=admin_zebor_headers,
    )

    assert response.status_code == 422


def test_isolasi_cabang_pengambilan_kas(
    client,
    admin_zebor_headers,
    seeded_ids,
):
    response = client.get(
        "/pengambilan-kas/pabrik",
        params={"cabang_id": seeded_ids["cabang_b"]},
        headers=admin_zebor_headers,
    )

    assert response.status_code == 403


def test_rentang_tanggal_pengambilan_kas_terbalik_ditolak(
    client,
    admin_zebor_headers,
    seeded_ids,
):
    response = client.get(
        "/pengambilan-kas/pabrik",
        params={
            "cabang_id": seeded_ids["zebor"],
            "tanggal_awal": "2099-03-10",
            "tanggal_akhir": "2099-03-01",
        },
        headers=admin_zebor_headers,
    )

    assert response.status_code == 422


@pytest.mark.parametrize(
    "sumber",
    ["pabrik", "balaraja"],
)
def test_karyawan_dapat_mengelola_pengambilan_kas(
    client,
    karyawan_zebor_headers,
    seeded_ids,
    sumber,
):
    table = {
        "pabrik": "pengambilan_pabrik",
        "balaraja": "pengambilan_balaraja",
    }[sumber]
    created_id = None

    try:
        create_response = client.post(
            f"/pengambilan-kas/{sumber}",
            headers=karyawan_zebor_headers,
            json={
                "cabang_id": seeded_ids["zebor"],
                "tanggal": "2099-03-05",
                "keterangan": "  Pengambilan API Test  ",
                "nominal": "325000",
            },
        )

        assert create_response.status_code == 200
        created_id = create_response.json()["id"]

        list_response = client.get(
            f"/pengambilan-kas/{sumber}",
            params={
                "cabang_id": seeded_ids["zebor"],
                "tanggal_awal": "2099-03-05",
                "tanggal_akhir": "2099-03-05",
            },
            headers=karyawan_zebor_headers,
        )

        assert list_response.status_code == 200

        created_row = next(
            row
            for row in list_response.json()
            if row[0] == created_id
        )

        assert created_row[3] == "Pengambilan API Test"
        assert money(created_row[4]) == Decimal("325000")

        update_response = client.put(
            f"/pengambilan-kas/{sumber}/{created_id}",
            headers=karyawan_zebor_headers,
            json={
                "tanggal": "2099-03-05",
                "keterangan": "Pengambilan diperbarui",
                "nominal": "425000",
            },
        )

        assert update_response.status_code == 200
        assert update_response.json() == {"ok": True}

        summary_response = client.get(
            f"/pengambilan-kas/{sumber}/summary",
            params={
                "cabang_id": seeded_ids["zebor"],
                "tanggal_awal": "2099-03-05",
                "tanggal_akhir": "2099-03-05",
            },
            headers=karyawan_zebor_headers,
        )

        assert summary_response.status_code == 200

        summary = summary_response.json()

        assert summary["total_data"] == 1
        assert money(summary["total_nominal"]) == Decimal("425000")

        delete_response = client.delete(
            f"/pengambilan-kas/{sumber}/{created_id}",
            headers=karyawan_zebor_headers,
        )

        assert delete_response.status_code == 200
        assert delete_response.json() == {"ok": True}

    finally:
        if created_id is not None:
            execute(
                """
                DELETE FROM activity_log
                WHERE entity = %s AND entity_id = %s
                """,
                (f"pengambilan_{sumber}", created_id),
            )
            execute(
                f"DELETE FROM {table} WHERE id = %s",
                (created_id,),
            )

def test_token_user_nonaktif_langsung_ditolak(
    client,
    karyawan_zebor_headers,
):
    execute(
        """
        UPDATE users
        SET aktif = FALSE
        WHERE username = %s
        """,
        ("karyawan_zebor_test",),
    )

    try:
        inactive_response = client.get(
            "/dashboard/summary",
            headers=karyawan_zebor_headers,
        )
    finally:
        execute(
            """
            UPDATE users
            SET aktif = TRUE
            WHERE username = %s
            """,
            ("karyawan_zebor_test",),
        )

    assert inactive_response.status_code == 401
    assert inactive_response.json()["detail"] == (
        "Akun tidak aktif, hubungi admin"
    )
    assert inactive_response.headers["www-authenticate"] == "Bearer"

    active_response = client.get(
        "/dashboard/summary",
        headers=karyawan_zebor_headers,
    )

    assert active_response.status_code == 200


def test_cabang_breakdown_tidak_menggandakan_modal(
    client,
    pusat_headers,
    seeded_ids,
):
    response = client.get(
        "/dashboard/cabang-breakdown",
        headers=pusat_headers,
    )

    assert response.status_code == 200

    zebor = next(
        item
        for item in response.json()
        if item["cabang_id"] == seeded_ids["zebor"]
    )

    assert money(zebor["modal_pusat"]) == Decimal("1000000")
    assert money(zebor["masuk_uang"]) == Decimal("1500000")
    assert money(zebor["masuk_barang"]) == Decimal("500000")


def test_monthly_trend_tidak_menggandakan_modal(
    client,
    admin_zebor_headers,
    seeded_ids,
):
    response = client.get(
        "/dashboard/monthly-trend",
        params={
            "cabang_id": seeded_ids["zebor"],
            "limit_months": 6,
        },
        headers=admin_zebor_headers,
    )

    assert response.status_code == 200

    januari = next(
        item
        for item in response.json()
        if item["bulan"] == 1 and item["tahun"] == 2099
    )

    assert money(januari["modal_pusat"]) == Decimal("1000000")
    assert money(januari["masuk_uang"]) == Decimal("1500000")
    assert money(januari["masuk_barang"]) == Decimal("500000")


def test_daftar_folder_tidak_menggandakan_modal(
    client,
    admin_zebor_headers,
    seeded_ids,
):
    response = client.get(
        "/folders",
        params={"cabang_id": seeded_ids["zebor"]},
        headers=admin_zebor_headers,
    )

    assert response.status_code == 200

    januari = next(
        row
        for row in response.json()
        if row[2] == 1 and row[3] == 2099
    )

    assert januari[5] == 1
    assert money(januari[6]) == Decimal("1000000")
    assert money(januari[7]) == Decimal("1500000")
    assert money(januari[8]) == Decimal("500000")