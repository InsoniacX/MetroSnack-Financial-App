import sys
from pathlib import Path

import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient


BACKEND_DIR = Path(__file__).resolve().parents[1]
ENV_FILE = BACKEND_DIR / ".env.test"
EXPECTED_DATABASE = "metrosnack_financial_test"

sys.path.insert(0, str(BACKEND_DIR))

if not ENV_FILE.exists():
    raise RuntimeError(f"File test tidak ditemukan: {ENV_FILE}")

load_dotenv(ENV_FILE, override=True)

from config import DB_CONFIG

if DB_CONFIG["dbname"] != EXPECTED_DATABASE:
    raise RuntimeError(
        f"Pytest menolak database '{DB_CONFIG['dbname']}'. "
        f"Gunakan '{EXPECTED_DATABASE}'."
    )

from main import app
from database import connection as db_connection
from database.connection import fetch_one


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as test_client:
        yield test_client

    db_connection.close_pool()


def login_headers(client, username, password):
    response = client.post(
        "/auth/login",
        json={
            "username": username,
            "password": password,
        },
    )

    assert response.status_code == 200, response.text

    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="session")
def pusat_headers(client):
    return login_headers(client, "pusat_test", "PusatTest123!")


@pytest.fixture(scope="session")
def admin_zebor_headers(client):
    return login_headers(
        client,
        "admin_zebor_test",
        "AdminZebor123!",
    )


@pytest.fixture(scope="session")
def karyawan_zebor_headers(client):
    return login_headers(
        client,
        "karyawan_zebor_test",
        "KaryawanZebor123!",
    )


@pytest.fixture(scope="session")
def cabang_b_headers(client):
    return login_headers(
        client,
        "karyawan_b_test",
        "KaryawanB123!",
    )


@pytest.fixture(scope="session")
def seeded_ids(client):
    def get_id(query, params):
        row = fetch_one(query, params)
        assert row is not None, (
            "Data seed tidak ditemukan. Jalankan seed_test_data.py."
        )
        return row[0]

    return {
        "zebor": get_id(
            "SELECT id FROM cabang WHERE nama_cabang = %s",
            ("Zebor",),
        ),
        "cabang_b": get_id(
            "SELECT id FROM cabang WHERE nama_cabang = %s",
            ("Cabang Test B",),
        ),
        "invoice_zebor": get_id(
            "SELECT id FROM invoice WHERE no_laporan = %s",
            ("TEST-ZEBOR-001",),
        ),
        "invoice_b": get_id(
            "SELECT id FROM invoice WHERE no_laporan = %s",
            ("TEST-B-001",),
        ),
        "supir_zebor": get_id(
            """
            SELECT id
            FROM supir_kenek
            WHERE nama = %s
            """,
            ("Supir Test",),
        ),
        "operasional_zebor": get_id(
            """
            SELECT id
            FROM operasional_mobil
            WHERE keterangan = %s
            """,
            ("Trip operasional test",),
        ),
        "pengambilan_pabrik_zebor": get_id(
            """
            SELECT id
            FROM pengambilan_pabrik
            WHERE keterangan = %s
            """,
            ("BAYAR TERIGU TEST",),
        ),
        "pengambilan_balaraja_zebor": get_id(
            """
            SELECT id
            FROM pengambilan_balaraja
            WHERE keterangan = %s
            """,
            ("SAGU TEST",),
        ),
    }