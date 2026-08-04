from config import MONTH
from db.connection import fetch_all, fetch_one, execute


def get_dashboard_summary():
    row = fetch_one("""
        SELECT
            COALESCE(SUM(t.masuk_uang), 0),
            COALESCE(SUM(t.masuk_barang), 0)
        FROM invoice i
        LEFT JOIN transaksi_harian t ON t.invoice_id = i.id
    """)
    omzet, barang = row
    laba_bersih = omzet - barang
    return {"omzet": omzet, "barang": barang, "laba_bersih": laba_bersih}


def get_folders():
    return fetch_all("""
        SELECT f.id, f.nama_folder, f.bulan, f.tahun,
            COUNT(DISTINCT i.id) AS total_invoice,
            COALESCE(SUM(t.masuk_uang), 0) - COALESCE(SUM(t.masuk_barang), 0) AS laba_bersih
        FROM folder_bulan f
        LEFT JOIN invoice i ON i.folder_bulan_id = f.id
        LEFT JOIN transaksi_harian t ON t.invoice_id = i.id
        GROUP BY f.id
        ORDER BY f.tahun DESC, f.bulan DESC
    """)


def create_folder(bulan, tahun, user_id):
    nama_folder = f"{MONTH[bulan]} {tahun}"
    return execute(
        "INSERT INTO folder_bulan (nama_folder, bulan, tahun, dibuat_oleh) VALUES (%s,%s,%s,%s) RETURNING id",
        (nama_folder, bulan, tahun, user_id),
        returning=True,
    )