from database.connection import fetch_all, fetch_one, execute


def get_entries(cabang_id, tanggal_awal=None, tanggal_akhir=None, jenis=None):
    """List entri, filter opsional rentang tanggal & jenis. Dipakai baik
    untuk 1 hari (tanggal_awal == tanggal_akhir) maupun 1 bulan penuh."""
    query = """
        SELECT id, cabang_id, tanggal, jenis, nama_pengeluaran, nominal, user_id, created_at, updated_at
        FROM pendapatan_pengeluaran_harian
        WHERE cabang_id = %s
    """
    params = [cabang_id]
    if tanggal_awal is not None:
        query += " AND tanggal >= %s"
        params.append(tanggal_awal)
    if tanggal_akhir is not None:
        query += " AND tanggal <= %s"
        params.append(tanggal_akhir)
    if jenis is not None:
        query += " AND jenis = %s"
        params.append(jenis)
    query += " ORDER BY tanggal DESC, id DESC"
    return fetch_all(query, tuple(params))


def get_entry_header(entry_id):
    """Dipakai cek kepemilikan cabang sebelum update/delete."""
    return fetch_one(
        "SELECT id, cabang_id FROM pendapatan_pengeluaran_harian WHERE id = %s",
        (entry_id,),
    )


def create_entry(cabang_id, tanggal, jenis, nama_pengeluaran, nominal, user_id):
    return execute("""
        INSERT INTO pendapatan_pengeluaran_harian
            (cabang_id, tanggal, jenis, nama_pengeluaran, nominal, user_id)
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING id
    """, (cabang_id, tanggal, jenis, nama_pengeluaran, nominal, user_id), returning=True)


def update_entry(entry_id, tanggal, jenis, nama_pengeluaran, nominal):
    execute("""
        UPDATE pendapatan_pengeluaran_harian
        SET tanggal = %s, jenis = %s, nama_pengeluaran = %s, nominal = %s
        WHERE id = %s
    """, (tanggal, jenis, nama_pengeluaran, nominal, entry_id))


def delete_entry(entry_id):
    execute("DELETE FROM pendapatan_pengeluaran_harian WHERE id = %s", (entry_id,))


def get_daily_summary(cabang_id, tanggal):
    """Total pendapatan/pengeluaran/bersih untuk 1 cabang di 1 tanggal."""
    row = fetch_one("""
        SELECT
            COALESCE(SUM(nominal) FILTER (WHERE jenis = 'pendapatan'), 0),
            COALESCE(SUM(nominal) FILTER (WHERE jenis = 'pengeluaran'), 0)
        FROM pendapatan_pengeluaran_harian
        WHERE cabang_id = %s AND tanggal = %s
    """, (cabang_id, tanggal))
    total_pendapatan, total_pengeluaran = row
    return {
        "tanggal": tanggal,
        "total_pendapatan": total_pendapatan,
        "total_pengeluaran": total_pengeluaran,
        "pendapatan_bersih": total_pendapatan - total_pengeluaran,
    }


def get_monthly_summary(cabang_id, bulan, tahun):
    """Akumulasi 1 bulan PLUS breakdown per-hari (buat grafik/tabel rincian)."""
    total_pendapatan, total_pengeluaran = fetch_one("""
        SELECT
            COALESCE(SUM(nominal) FILTER (WHERE jenis = 'pendapatan'), 0),
            COALESCE(SUM(nominal) FILTER (WHERE jenis = 'pengeluaran'), 0)
        FROM pendapatan_pengeluaran_harian
        WHERE cabang_id = %s
          AND EXTRACT(MONTH FROM tanggal) = %s
          AND EXTRACT(YEAR FROM tanggal) = %s
    """, (cabang_id, bulan, tahun))

    per_hari = fetch_all("""
        SELECT tanggal,
            COALESCE(SUM(nominal) FILTER (WHERE jenis = 'pendapatan'), 0),
            COALESCE(SUM(nominal) FILTER (WHERE jenis = 'pengeluaran'), 0)
        FROM pendapatan_pengeluaran_harian
        WHERE cabang_id = %s
          AND EXTRACT(MONTH FROM tanggal) = %s
          AND EXTRACT(YEAR FROM tanggal) = %s
        GROUP BY tanggal
        ORDER BY tanggal
    """, (cabang_id, bulan, tahun))

    return {
        "bulan": bulan,
        "tahun": tahun,
        "total_pendapatan": total_pendapatan,
        "total_pengeluaran": total_pengeluaran,
        "pendapatan_bersih": total_pendapatan - total_pengeluaran,
        "per_hari": [
            {"tanggal": r[0], "total_pendapatan": r[1], "total_pengeluaran": r[2], "pendapatan_bersih": r[1] - r[2]}
            for r in per_hari
        ],
    }