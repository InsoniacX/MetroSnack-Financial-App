from database.connection import fetch_all, fetch_one, execute


def get_transaksi(invoice_id):
    return fetch_all("""
        SELECT id, tanggal_transaksi, masuk_barang, masuk_uang, lebih_kurang, keterangan
        FROM transaksi_harian WHERE invoice_id=%s ORDER BY tanggal_transaksi
    """, (invoice_id,))

def add_transaksi(invoice_id, tanggal, masuk_barang, masuk_uang):
    execute("""
        INSERT INTO transaksi_harian (invoice_id, tanggal_transaksi, masuk_barang, masuk_uang)
        VALUES (%s,%s,%s,%s)
    """, (invoice_id, tanggal, masuk_barang, masuk_uang))

def delete_transaksi(t_id):
    execute("DELETE FROM transaksi_harian WHERE id=%s", (t_id,))

def update_transaksi(t_id, tanggal, masuk_barang, masuk_uang):
    execute("""
        UPDATE transaksi_harian SET tanggal_transaksi=%s, masuk_barang=%s, masuk_uang=%s
        WHERE id=%s
    """, (tanggal, masuk_barang, masuk_uang, t_id))

def get_transaksi_cabang_id(t_id):
    """Cari cabang_id pemilik transaksi ini, lewat invoice -> folder_bulan -> cabang.
    Dipakai untuk cek isolasi cabang sebelum update/delete."""
    row = fetch_one("""
        SELECT f.cabang_id
        FROM transaksi_harian t
        JOIN invoice i ON i.id = t.invoice_id
        JOIN folder_bulan f ON f.id = i.folder_bulan_id
        WHERE t.id = %s
    """, (t_id,))
    return row[0] if row else None
