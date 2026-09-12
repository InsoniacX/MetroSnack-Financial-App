"""Read-only monthly aggregates. Carry-forward is never stored as new debt."""
from database.connection import fetch_all


def get_monthly_totals(cabang_id=None, through_folder_id=None, active_only=False):
    folder_filters = []
    branch_filters = []
    params = []
    if cabang_id is not None:
        folder_filters.append("f.cabang_id = %s")
        params.append(cabang_id)
    if through_folder_id is not None:
        folder_filters.append("""(f.tahun, f.bulan) <= (
            SELECT tahun, bulan FROM folder_bulan WHERE id = %s
        )""")
        params.append(through_folder_id)
    if cabang_id is not None:
        branch_filters.append("c.id = %s")
        params.append(cabang_id)
    if active_only:
        branch_filters.append("c.aktif = TRUE")
    folder_where = "WHERE " + " AND ".join(folder_filters) if folder_filters else ""
    branch_where = "WHERE " + " AND ".join(branch_filters) if branch_filters else ""

    # Aggregate per invoice before summing per month: multiple transactions
    # must not multiply invoice_bon. Empty folders and branches are retained.
    rows = fetch_all(f"""
        WITH per_invoice AS (
            SELECT f.id AS folder_id, f.cabang_id, f.nama_folder, f.tahun, f.bulan,
                   i.id AS invoice_id, COALESCE(i.invoice_bon, 0) AS modal_pusat,
                   COALESCE(SUM(t.masuk_uang), 0) AS masuk_uang,
                   COALESCE(SUM(t.masuk_barang), 0) AS masuk_barang
            FROM folder_bulan f
            LEFT JOIN invoice i ON i.folder_bulan_id = f.id
            LEFT JOIN transaksi_harian t ON t.invoice_id = i.id
            {folder_where}
            GROUP BY f.id, i.id
        )
        SELECT c.id, c.nama_cabang, p.folder_id, p.nama_folder, p.tahun, p.bulan,
               COUNT(p.invoice_id), COALESCE(SUM(p.modal_pusat), 0),
               COALESCE(SUM(p.masuk_uang), 0), COALESCE(SUM(p.masuk_barang), 0)
        FROM cabang c
        LEFT JOIN per_invoice p ON p.cabang_id = c.id
        {branch_where}
        GROUP BY c.id, p.folder_id, p.nama_folder, p.tahun, p.bulan
        ORDER BY c.id, p.tahun, p.bulan
    """, tuple(params))
    keys = ("cabang_id", "nama_cabang", "folder_id", "nama_folder", "tahun", "bulan",
            "total_invoice", "modal_pusat", "masuk_uang", "masuk_barang")
    return [dict(zip(keys, row)) for row in rows]
