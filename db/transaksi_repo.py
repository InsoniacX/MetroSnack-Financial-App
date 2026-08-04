from db.connection import fetch_all, execute


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