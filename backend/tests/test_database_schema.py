from database.connection import fetch_all


EXPECTED_TABLES = {
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
}

EXPECTED_CONSTRAINTS = {
    "invoice_invoice_bon_nonnegative",
    "invoice_sisa_barang_manual_nonnegative",
    "transaksi_harian_masuk_barang_nonnegative",
    "transaksi_harian_masuk_uang_nonnegative",
}


def test_seluruh_tabel_tersedia():
    rows = fetch_all(
        """
        SELECT tablename
        FROM pg_tables
        WHERE schemaname = 'public'
        """
    )

    actual = {row[0] for row in rows}
    assert EXPECTED_TABLES <= actual


def test_constraint_migration_004_tersedia():
    rows = fetch_all(
        """
        SELECT conname
        FROM pg_constraint
        WHERE conname = ANY(%s)
        """,
        (list(EXPECTED_CONSTRAINTS),),
    )

    actual = {row[0] for row in rows}
    assert actual == EXPECTED_CONSTRAINTS