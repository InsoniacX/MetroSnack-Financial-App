from database.connection import fetch_all, fetch_one, execute


def get_invoice_ids(folder_id):
    """Query RINGAN: cuma id invoice, tanpa JOIN/SUM ke transaksi_harian."""
    rows = fetch_all("SELECT id FROM invoice WHERE folder_bulan_id = %s ORDER BY id", (folder_id,))
    return [r[0] for r in rows]


def get_invoices(folder_id):
    """invoice_bon = Modal Pusat / Nilai Awal (dikonfirmasi 19 Agustus 2026)."""
    return fetch_all("""
        SELECT i.id, i.no_laporan, i.tanggal_dibuat, i.tanggal_laporan, i.invoice_bon,
            COALESCE(SUM(t.masuk_uang), 0) AS total_omzet,
            COALESCE(SUM(t.masuk_barang), 0) AS total_barang
        FROM invoice i
        LEFT JOIN transaksi_harian t ON t.invoice_id = i.id
        WHERE i.folder_bulan_id = %s
        GROUP BY i.id
        ORDER BY i.tanggal_laporan DESC
    """, (folder_id,))


def create_invoice(folder_id, no_laporan, tanggal_dibuat, tanggal_laporan, invoice_bon, user_id):
    return execute("""
        INSERT INTO invoice (folder_bulan_id, no_laporan, tanggal_dibuat, tanggal_laporan, invoice_bon, dibuat_oleh)
        VALUES (%s,%s,%s,%s,%s,%s) RETURNING id
    """, (folder_id, no_laporan, tanggal_dibuat, tanggal_laporan, invoice_bon, user_id), returning=True)


def delete_invoice(invoice_id):
    execute("DELETE FROM invoice WHERE id=%s", (invoice_id,))


def get_invoice_header(invoice_id):
    return fetch_one("""
        SELECT i.id, i.no_laporan, i.tanggal_dibuat, i.tanggal_laporan, i.invoice_bon,
            i.folder_bulan_id, f.cabang_id, i.sisa_barang_manual
        FROM invoice i
        JOIN folder_bulan f ON f.id = i.folder_bulan_id
        WHERE i.id=%s
    """, (invoice_id,))


def update_invoice(invoice_id, no_laporan, tanggal_dibuat, tanggal_laporan, invoice_bon):
    execute("""
        UPDATE invoice SET no_laporan=%s, tanggal_dibuat=%s, tanggal_laporan=%s, invoice_bon=%s
        WHERE id=%s
    """, (no_laporan, tanggal_dibuat, tanggal_laporan, invoice_bon, invoice_id))


def get_invoice_totals(invoice_id):
    """Untuk hitung Sisa Hutang lewat finance_service: invoice_bon (=modal) + total masuk_uang/masuk_barang."""
    return fetch_one("""
        SELECT i.invoice_bon,
            COALESCE(SUM(t.masuk_uang), 0) AS total_masuk_uang,
            COALESCE(SUM(t.masuk_barang), 0) AS total_masuk_barang
        FROM invoice i
        LEFT JOIN transaksi_harian t ON t.invoice_id = i.id
        WHERE i.id = %s
        GROUP BY i.invoice_bon
    """, (invoice_id,))


def update_sisa_barang_manual(invoice_id, value):
    """Item #3: update nilai Sisa Barang di Toko yang diinput manual staff.
    Endpoint terpisah dari update_invoice() supaya staff bisa update ini
    tiap hari tanpa perlu isi ulang field invoice lain."""
    execute("UPDATE invoice SET sisa_barang_manual=%s WHERE id=%s", (value, invoice_id))
