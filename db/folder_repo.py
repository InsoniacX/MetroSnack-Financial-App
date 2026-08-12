from config import MONTH
from db.connection import fetch_all, fetch_one, execute


def get_dashboard_summary(cabang_id=None):
    if cabang_id is None:
        row = fetch_one("""
            SELECT COALESCE(SUM(t.masuk_uang), 0), COALESCE(SUM(t.masuk_barang), 0)
            FROM invoice i
            LEFT JOIN transaksi_harian t ON t.invoice_id = i.id
        """)
    else:
        row = fetch_one("""
            SELECT COALESCE(SUM(t.masuk_uang), 0), COALESCE(SUM(t.masuk_barang), 0)
            FROM invoice i
            JOIN folder_bulan f ON f.id = i.folder_bulan_id
            LEFT JOIN transaksi_harian t ON t.invoice_id = i.id
            WHERE f.cabang_id = %s
        """, (cabang_id,))
    omzet, barang = row
    laba_bersih = omzet - barang
    return {"omzet": omzet, "barang": barang, "laba_bersih": laba_bersih}

def get_cabang_breakdown():
    """Pemasukan (omzet) & pengeluaran (masuk barang) per cabang -> untuk pie chart Dashboard Admin Pusat."""
    return fetch_all("""
        SELECT c.id, c.nama_cabang,
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
    """Ringkasan per cabang (total folder + laba bersih) untuk halaman 'Pilih Cabang' Admin Pusat."""
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

def get_monthly_trend(cabang_id=None, limit_months=6):
    if cabang_id is None:
        rows = fetch_all("""
            SELECT f.id, f.nama_folder, f.bulan, f.tahun,
                COALESCE(SUM(t.masuk_uang), 0) AS total_omzet,
                COALESCE(SUM(t.masuk_uang), 0) - COALESCE(SUM(t.masuk_barang), 0) AS laba_bersih
            FROM folder_bulan f
            LEFT JOIN invoice i ON i.folder_bulan_id = f.id
            LEFT JOIN transaksi_harian t ON t.invoice_id = i.id
            GROUP BY f.id
            ORDER BY f.tahun DESC, f.bulan DESC
            LIMIT %s
        """, (limit_months,))
    else:
        rows = fetch_all("""
            SELECT f.id, f.nama_folder, f.bulan, f.tahun,
                COALESCE(SUM(t.masuk_uang), 0) AS total_omzet,
                COALESCE(SUM(t.masuk_uang), 0) - COALESCE(SUM(t.masuk_barang), 0) AS laba_bersih
            FROM folder_bulan f
            LEFT JOIN invoice i ON i.folder_bulan_id = f.id
            LEFT JOIN transaksi_harian t ON t.invoice_id = i.id
            WHERE f.cabang_id = %s
            GROUP BY f.id
            ORDER BY f.tahun DESC, f.bulan DESC
            LIMIT %s
        """, (cabang_id, limit_months))
    return list(reversed(rows))


def get_folders(cabang_id=None):
    if cabang_id is None:
        return fetch_all("""
            SELECT f.id, f.nama_folder, f.bulan, f.tahun, c.nama_cabang,
                COUNT(DISTINCT i.id) AS total_invoice,
                COALESCE(SUM(t.masuk_uang), 0) - COALESCE(SUM(t.masuk_barang), 0) AS laba_bersih
            FROM folder_bulan f
            JOIN cabang c ON c.id = f.cabang_id
            LEFT JOIN invoice i ON i.folder_bulan_id = f.id
            LEFT JOIN transaksi_harian t ON t.invoice_id = i.id
            GROUP BY f.id, c.nama_cabang
            ORDER BY f.tahun DESC, f.bulan DESC
        """)
    return fetch_all("""
        SELECT f.id, f.nama_folder, f.bulan, f.tahun, c.nama_cabang,
            COUNT(DISTINCT i.id) AS total_invoice,
            COALESCE(SUM(t.masuk_uang), 0) - COALESCE(SUM(t.masuk_barang), 0) AS laba_bersih
        FROM folder_bulan f
        JOIN cabang c ON c.id = f.cabang_id
        LEFT JOIN invoice i ON i.folder_bulan_id = f.id
        LEFT JOIN transaksi_harian t ON t.invoice_id = i.id
        WHERE f.cabang_id = %s
        GROUP BY f.id, c.nama_cabang
        ORDER BY f.tahun DESC, f.bulan DESC
    """, (cabang_id,))


def create_folder(bulan, tahun, cabang_id, user_id):
    nama_folder = f"{MONTH[bulan]} {tahun}"
    return execute(
        "INSERT INTO folder_bulan (nama_folder, bulan, tahun, cabang_id, dibuat_oleh) VALUES (%s,%s,%s,%s,%s) RETURNING id",
        (nama_folder, bulan, tahun, cabang_id, user_id),
        returning=True,
    )


def get_folder_header(folder_id):
    return fetch_one("""
        SELECT f.id, f.nama_folder, f.cabang_id, c.nama_cabang
        FROM folder_bulan f
        JOIN cabang c ON c.id = f.cabang_id
        WHERE f.id = %s
    """, (folder_id,))

def delete_folder(folder_id):
    """Menghapus folder_bulan. Skema DB sudah ON DELETE CASCADE ke invoice -> transaksi_harian,
    jadi semua data di dalamnya ikut terhapus otomatis."""
    execute("DELETE FROM folder_bulan WHERE id=%s", (folder_id,))