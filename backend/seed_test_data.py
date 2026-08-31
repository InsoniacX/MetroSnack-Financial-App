from datetime import date
from decimal import Decimal
from pathlib import Path

import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import execute_values


BASE_DIR = Path(__file__).resolve().parent
ENV_FILE = BASE_DIR / ".env.test"
EXPECTED_DATABASE = "metrosnack_financial_test"

if not ENV_FILE.exists():
    raise RuntimeError(
        f"File {ENV_FILE} tidak ditemukan. "
        "Buat .env.test sebelum menjalankan seeder."
    )

# Harus dilakukan sebelum mengimpor config dan auth.security.
load_dotenv(ENV_FILE, override=True)

from config import DB_CONFIG
from auth.security import hash_password


REQUIRED_TABLES = (
    "cabang",
    "users",
    "folder_bulan",
    "invoice",
    "transaksi_harian",
    "activity_log",
    "pendapatan_pengeluaran_harian",
    "supir_kenek",
    "operasional_mobil",
    "pengambilan_pabrik",
    "pengambilan_balaraja",
)

TEST_PASSWORDS = {
    "pusat_test": "PusatTest123!",
    "admin_zebor_test": "AdminZebor123!",
    "karyawan_zebor_test": "KaryawanZebor123!",
    "karyawan_b_test": "KaryawanB123!",
}


def insert_user(
    cursor,
    username,
    password_hash,
    nama_lengkap,
    role,
    cabang_id,
):
    cursor.execute(
        """
        INSERT INTO users (
            username,
            password_hash,
            nama_lengkap,
            role,
            aktif,
            cabang_id
        )
        VALUES (%s, %s, %s, %s, TRUE, %s)
        RETURNING id
        """,
        (
            username,
            password_hash,
            nama_lengkap,
            role,
            cabang_id,
        ),
    )
    return cursor.fetchone()[0]


def main():
    if DB_CONFIG["dbname"] != EXPECTED_DATABASE:
        raise RuntimeError(
            "Seeder dibatalkan. DB_NAME harus tepat "
            f"'{EXPECTED_DATABASE}', tetapi sekarang "
            f"'{DB_CONFIG['dbname']}'."
        )

    # Hash dibuat sebelum transaksi agar transaksi database tetap singkat.
    password_hashes = {
        username: hash_password(password)
        for username, password in TEST_PASSWORDS.items()
    }

    connection = psycopg2.connect(**DB_CONFIG)

    try:
        if connection.info.dbname != EXPECTED_DATABASE:
            raise RuntimeError(
                f"Seeder menolak database '{connection.info.dbname}'."
            )

        with connection:
            with connection.cursor() as cursor:
                cursor.execute("SET LOCAL statement_timeout = '30s'")

                missing_tables = []

                for table_name in REQUIRED_TABLES:
                    cursor.execute(
                        "SELECT to_regclass(%s)",
                        (f"public.{table_name}",),
                    )
                    if cursor.fetchone()[0] is None:
                        missing_tables.append(table_name)

                if missing_tables:
                    raise RuntimeError(
                        "Migration belum lengkap. Tabel tidak ditemukan: "
                        + ", ".join(missing_tables)
                    )

                # Aman hanya karena ada pemeriksaan nama database di atas.
                cursor.execute(
                    """
                    TRUNCATE TABLE
                        activity_log,
                        operasional_mobil,
                        pengambilan_pabrik,
                        pengambilan_balaraja,
                        pendapatan_pengeluaran_harian,
                        supir_kenek,
                        transaksi_harian,
                        invoice,
                        folder_bulan,
                        users,
                        cabang
                    RESTART IDENTITY CASCADE
                    """
                )

                cursor.execute(
                    """
                    INSERT INTO cabang (nama_cabang, alamat, aktif)
                    VALUES ('Zebor', 'Alamat Test Zebor', TRUE)
                    RETURNING id
                    """
                )
                zebor_id = cursor.fetchone()[0]

                cursor.execute(
                    """
                    INSERT INTO cabang (nama_cabang, alamat, aktif)
                    VALUES ('Cabang Test B', 'Alamat Test B', TRUE)
                    RETURNING id
                    """
                )
                cabang_b_id = cursor.fetchone()[0]

                pusat_id = insert_user(
                    cursor,
                    "pusat_test",
                    password_hashes["pusat_test"],
                    "Admin Pusat Test",
                    "admin",
                    None,
                )

                admin_zebor_id = insert_user(
                    cursor,
                    "admin_zebor_test",
                    password_hashes["admin_zebor_test"],
                    "Admin Zebor Test",
                    "admin",
                    zebor_id,
                )

                insert_user(
                    cursor,
                    "karyawan_zebor_test",
                    password_hashes["karyawan_zebor_test"],
                    "Karyawan Zebor Test",
                    "karyawan",
                    zebor_id,
                )

                karyawan_b_id = insert_user(
                    cursor,
                    "karyawan_b_test",
                    password_hashes["karyawan_b_test"],
                    "Karyawan Cabang B Test",
                    "karyawan",
                    cabang_b_id,
                )

                cursor.execute(
                    """
                    INSERT INTO folder_bulan (
                        nama_folder,
                        bulan,
                        tahun,
                        dibuat_oleh,
                        cabang_id
                    )
                    VALUES ('Januari 2099', 1, 2099, %s, %s)
                    RETURNING id
                    """,
                    (admin_zebor_id, zebor_id),
                )
                folder_zebor_id = cursor.fetchone()[0]

                cursor.execute(
                    """
                    INSERT INTO folder_bulan (
                        nama_folder,
                        bulan,
                        tahun,
                        dibuat_oleh,
                        cabang_id
                    )
                    VALUES ('Januari 2099', 1, 2099, %s, %s)
                    RETURNING id
                    """,
                    (karyawan_b_id, cabang_b_id),
                )
                folder_b_id = cursor.fetchone()[0]

                cursor.execute(
                    """
                    INSERT INTO invoice (
                        folder_bulan_id,
                        no_laporan,
                        tanggal_dibuat,
                        tanggal_laporan,
                        invoice_bon,
                        dibuat_oleh,
                        sisa_barang_manual
                    )
                    VALUES (
                        %s,
                        'TEST-ZEBOR-001',
                        %s,
                        %s,
                        %s,
                        %s,
                        %s
                    )
                    RETURNING id
                    """,
                    (
                        folder_zebor_id,
                        date(2099, 1, 1),
                        date(2099, 1, 31),
                        Decimal("1000000"),
                        admin_zebor_id,
                        Decimal("100000"),
                    ),
                )
                invoice_zebor_id = cursor.fetchone()[0]

                cursor.execute(
                    """
                    INSERT INTO invoice (
                        folder_bulan_id,
                        no_laporan,
                        tanggal_dibuat,
                        tanggal_laporan,
                        invoice_bon,
                        dibuat_oleh
                    )
                    VALUES (
                        %s,
                        'TEST-B-001',
                        %s,
                        %s,
                        %s,
                        %s
                    )
                    RETURNING id
                    """,
                    (
                        folder_b_id,
                        date(2099, 1, 1),
                        date(2099, 1, 31),
                        Decimal("800000"),
                        karyawan_b_id,
                    ),
                )
                invoice_b_id = cursor.fetchone()[0]

                # Zebor tepat lunas:
                # modal 1.000.000
                # masuk uang 1.500.000
                # masuk barang 500.000
                # selisih 1.000.000
                # sisa hutang 0
                execute_values(
                    cursor,
                    """
                    INSERT INTO transaksi_harian (
                        invoice_id,
                        tanggal_transaksi,
                        masuk_barang,
                        masuk_uang,
                        nota
                    )
                    VALUES %s
                    """,
                    [
                        (
                            invoice_zebor_id,
                            date(2099, 1, 10),
                            Decimal("300000"),
                            Decimal("700000"),
                            "TEST-NOTA-001",
                        ),
                        (
                            invoice_zebor_id,
                            date(2099, 1, 20),
                            Decimal("200000"),
                            Decimal("800000"),
                            "TEST-NOTA-002",
                        ),
                        (
                            invoice_b_id,
                            date(2099, 1, 15),
                            Decimal("200000"),
                            Decimal("500000"),
                            "TEST-NOTA-B-001",
                        ),
                    ],
                )

                execute_values(
                    cursor,
                    """
                    INSERT INTO pendapatan_pengeluaran_harian (
                        cabang_id,
                        tanggal,
                        jenis,
                        nama_pengeluaran,
                        nominal,
                        user_id
                    )
                    VALUES %s
                    """,
                    [
                        (
                            zebor_id,
                            date(2099, 1, 10),
                            "pendapatan",
                            "Pendapatan Test",
                            Decimal("2000000"),
                            admin_zebor_id,
                        ),
                        (
                            zebor_id,
                            date(2099, 1, 10),
                            "pengeluaran",
                            "Listrik Test",
                            Decimal("500000"),
                            admin_zebor_id,
                        ),
                        (
                            zebor_id,
                            date(2099, 1, 11),
                            "pengeluaran",
                            "Transport Test",
                            Decimal("250000"),
                            admin_zebor_id,
                        ),
                    ],
                )

                cursor.execute(
                    """
                    INSERT INTO supir_kenek (cabang_id, nama)
                    VALUES (%s, 'Supir Test')
                    RETURNING id
                    """,
                    (zebor_id,),
                )
                supir_id = cursor.fetchone()[0]

                cursor.execute(
                    """
                    INSERT INTO supir_kenek (cabang_id, nama)
                    VALUES (%s, 'Kenek Test')
                    RETURNING id
                    """,
                    (zebor_id,),
                )
                kenek_id = cursor.fetchone()[0]

                cursor.execute(
                    """
                    INSERT INTO operasional_mobil (
                        cabang_id,
                        tanggal,
                        supir_id,
                        kenek_id,
                        uang_jalan,
                        keterangan,
                        user_id
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        zebor_id,
                        date(2099, 1, 12),
                        supir_id,
                        kenek_id,
                        Decimal("150000"),
                        "Trip operasional test",
                        admin_zebor_id,
                    ),
                )

                cursor.execute(
                    """
                    INSERT INTO pengambilan_pabrik (
                        cabang_id,
                        tanggal,
                        keterangan,
                        nominal,
                        user_id
                    )
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        zebor_id,
                        date(2099, 1, 13),
                        "BAYAR TERIGU TEST",
                        Decimal("1000000"),
                        admin_zebor_id,
                    ),
                )

                cursor.execute(
                    """
                    INSERT INTO pengambilan_balaraja (
                        cabang_id,
                        tanggal,
                        keterangan,
                        nominal,
                        user_id
                    )
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        zebor_id,
                        date(2099, 1, 14),
                        "SAGU TEST",
                        Decimal("750000"),
                        admin_zebor_id,
                    ),
                )

                cursor.execute(
                    """
                    INSERT INTO activity_log (
                        user_id,
                        username,
                        action,
                        entity,
                        entity_id,
                        description,
                        cabang_id
                    )
                    VALUES (%s, %s, 'CREATE', 'seed', NULL, %s, NULL)
                    """,
                    (
                        pusat_id,
                        "pusat_test",
                        "Data automated testing dibuat",
                    ),
                )

        print(f"Seed berhasil pada database: {EXPECTED_DATABASE}")
        print("Akun test:")
        for username, password in TEST_PASSWORDS.items():
            print(f"  {username} / {password}")

    finally:
        connection.close()


if __name__ == "__main__":
    main()