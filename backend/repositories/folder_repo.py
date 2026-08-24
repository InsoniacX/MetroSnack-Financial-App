from database.connection import fetch_all, fetch_one, execute

MONTH = {
    1: "Januari", 2: "Februari", 3: "Maret", 4: "April", 5: "Mei", 6: "Juni",
    7: "Juli", 8: "Agustus", 9: "September", 10: "Oktober", 11: "November", 12: "Desember",
}


def get_dashboard_summary_raw(cabang_id=None):
    """Angka mentah saja (modal, masuk_uang, masuk_barang). Perhitungan
    Lebih/Kurang/Sisa Hutang dilakukan di services/finance_service.py,
    BUKAN di sini, supaya tetap satu sumber kebenaran formula."""
    if cabang_id is None:
        row = fetch_one("""
            SELECT COALESCE(SUM(i.invoice_bon), 0), COALESCE(SUM(t.masuk_uang), 0), COALESCE(SUM(t.masuk_barang), 0)
            FROM invoice i
            LEFT JOIN transaksi_harian t ON t.invoice_id = i.id
        """)
    else:
        row = fetch_one("""
            SELECT COALESCE(SUM(i.invoice_bon), 0), COALESCE(SUM(t.masuk_uang), 0), COALESCE(SUM(t.masuk_barang), 0)
            FROM invoice i
            JOIN folder_bulan f ON f.id = i.folder_bulan_id
            LEFT JOIN transaksi_harian t ON t.invoice_id = i.id
            WHERE f.cabang_id = %s
        """, (cabang_id,))
    modal, omzet, barang = row
    return {"modal_pusat": modal, "masuk_uang": omzet, "masuk_barang": barang}


def get_cabang_breakdown():
    """Per-cabang: modal, masuk_uang, masuk_barang mentah -> dipakai dashboard admin pusat."""
    return fetch_all("""
        SELECT c.id, c.nama_cabang,
            COALESCE(SUM(i.invoice_bon), 0) AS total_modal,
            COALESCE(SUM(t.masuk_uang), 0) AS total_omzet,
            COALESCE(SUM(t.masuk_barang), 0) AS total_barang
        FROM cabang c
        LEFT JOIN folder_bulan f ON f.cabang_id = c.id
        LEFT JOIN invoice i ON i.folder_bulan_id = f.id
        LEFT JOIN transaksi_harian t ON t.invoice_id = i.id
        WHERE c.aktif = TRUE
        GROUP BY c.id, c.nama_cabang
        ORDER BY c.nama_cabang
    """)


def get_cabang_summary():
    """Ringkasan sederhana per-cabang (total folder + laba_bersih = omzet-barang,
    BUKAN Sisa Hutang) -> dipakai kartu 'Pilih Cabang' di invoices_view.py lama."""
    return fetch_all("""
        SELECT c.id, c.nama_cabang,
            COUNT(DISTINCT f.id) AS total_folder,
            COALESCE(SUM(t.masuk_uang), 0) - COALESCE(SUM(t.masuk_barang), 0) AS laba_bersih
        FROM cabang c
        LEFT JOIN folder_bulan f ON f.cabang_id = c.id
        LEFT JOIN invoice i ON i.folder_bulan_id = f.id
        LEFT JOIN transaksi_harian t ON t.invoice_id = i.id
        WHERE c.aktif = TRUE
        GROUP BY c.id, c.nama_cabang
        ORDER BY c.nama_cabang
    """)


def get_monthly_trend_raw(cabang_id=None, limit_months=6):
    base_select = """
        SELECT f.id, f.nama_folder, f.bulan, f.tahun,
            COALESCE(SUM(i.invoice_bon), 0) AS total_modal,
            COALESCE(SUM(t.masuk_uang), 0) AS total_omzet,
            COALESCE(SUM(t.masuk_barang), 0) AS total_barang
        FROM folder_bulan f
        LEFT JOIN invoice i ON i.folder_bulan_id = f.id
        LEFT JOIN transaksi_harian t ON t.invoice_id = i.id
    """
    if cabang_id is None:
        rows = fetch_all(base_select + " GROUP BY f.id ORDER BY f.tahun DESC, f.bulan DESC LIMIT %s", (limit_months,))
    else:
        rows = fetch_all(base_select + " WHERE f.cabang_id = %s GROUP BY f.id ORDER BY f.tahun DESC, f.bulan DESC LIMIT %s",
                          (cabang_id, limit_months))
    return list(reversed(rows))


def get_folders(cabang_id=None):
    base_select = """
        SELECT f.id, f.nama_folder, f.bulan, f.tahun, c.nama_cabang,
            COUNT(DISTINCT i.id) AS total_invoice,
            COALESCE(SUM(i.invoice_bon), 0) AS total_modal,
            COALESCE(SUM(t.masuk_uang), 0) AS total_omzet,
            COALESCE(SUM(t.masuk_barang), 0) AS total_barang
        FROM folder_bulan f
        JOIN cabang c ON c.id = f.cabang_id
        LEFT JOIN invoice i ON i.folder_bulan_id = f.id
        LEFT JOIN transaksi_harian t ON t.invoice_id = i.id
    """
    if cabang_id is None:
        return fetch_all(base_select + " GROUP BY f.id, c.nama_cabang ORDER BY f.tahun DESC, f.bulan DESC")
    return fetch_all(base_select + " WHERE f.cabang_id = %s GROUP BY f.id, c.nama_cabang ORDER BY f.tahun DESC, f.bulan DESC",
                      (cabang_id,))


def create_folder(bulan, tahun, cabang_id, user_id):
    nama_folder = f"{MONTH[bulan]} {tahun}"
    return execute(
        "INSERT INTO folder_bulan (nama_folder, bulan, tahun, cabang_id, dibuat_oleh) VALUES (%s,%s,%s,%s,%s) RETURNING id",
        (nama_folder, bulan, tahun, cabang_id, user_id), returning=True,
    )


def get_folder_header(folder_id):
    return fetch_one("""
        SELECT f.id, f.nama_folder, f.cabang_id, c.nama_cabang
        FROM folder_bulan f JOIN cabang c ON c.id = f.cabang_id
        WHERE f.id = %s
    """, (folder_id,))


def delete_folder(folder_id):
    """Skema DB pakai ON DELETE CASCADE ke invoice -> transaksi_harian."""
    execute("DELETE FROM folder_bulan WHERE id=%s", (folder_id,))
