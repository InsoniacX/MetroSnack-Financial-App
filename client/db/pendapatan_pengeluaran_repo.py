from decimal import Decimal
from datetime import date, datetime
from .http_client import api_get, api_post, api_put, api_delete, ApiError
from ._convert import to_date, to_decimal
from .cabang_repo import get_active_cabang, get_cabang_name

DEFAULT_KATEGORI_PENDAPATAN = [
    "Penjualan Langsung",
    "Penjualan Grosir",
    "Pendapatan Lain",
    "Komisi / Cashback",
    "Investasi / Modal",
]

DEFAULT_KATEGORI_PENGELUARAN = [
    "Bahan Baku",
    "Operasional",
    "Gaji",
    "Sewa",
    "Listrik & Air",
    "Transportasi & Logistik",
    "Kemasan & Perlengkapan",
    "Perbaikan & Perawatan",
    "Lain-lain",
]


def _iso(value):
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _parse_item_name(nama_str):
    """
    Ekstrak kategori dan keterangan dari kolom nama_pengeluaran.
    Format yang didukung:
    - '[Kategori] Keterangan'
    - 'Kategori - Keterangan'
    - 'Keterangan' (default kategori: 'Lain-lain')
    """
    nama = str(nama_str or "").strip()
    if not nama:
        return "Lain-lain", ""
    if nama.startswith("[") and "]" in nama:
        parts = nama[1:].split("]", 1)
        kat = parts[0].strip()
        ket = parts[1].strip()
        return kat or "Lain-lain", ket or kat
    if " - " in nama:
        parts = nama.split(" - ", 1)
        kat = parts[0].strip()
        ket = parts[1].strip()
        return kat or "Lain-lain", ket or kat
    return "Lain-lain", nama


def _format_item_name(kategori, keterangan):
    """Menggabungkan kategori dan keterangan menjadi format nama_pengeluaran backend."""
    ket = (keterangan or "").strip()
    kat = (kategori or "").strip()
    if kat and kat not in ("Lain-lain", "") and (kat.lower() not in ket.lower()):
        return f"[{kat}] {ket}" if ket else kat
    return ket or kat or "Transaksi Kas"


def get_transaksi_kas(
    cabang_id=None,
    bulan=None,
    tahun=None,
    start_date=None,
    end_date=None,
    jenis=None,
    kategori=None,
    search=None,
    sort_order="desc",
):
    """
    Mengambil daftar transaksi pendapatan/pengeluaran dari backend API.
    Mendukung filter cabang_id, rentang tanggal, bulan/tahun, jenis, kategori, dan search keyword.
    """
    cabang_name_map = {}
    try:
        active_cabangs = get_active_cabang()
        cabang_name_map = {c[0]: c[1] for c in active_cabangs}
    except Exception:
        pass

    raw_rows = []
    if cabang_id is not None:
        params = {"cabang_id": cabang_id, "limit": 500}
        if start_date:
            params["tanggal_awal"] = _iso(start_date)
        if end_date:
            params["tanggal_akhir"] = _iso(end_date)
        if jenis and str(jenis).lower() in ("pendapatan", "pengeluaran"):
            params["jenis"] = str(jenis).lower()

        try:
            resp = api_get("/pendapatan-pengeluaran", params=params)
            if resp:
                raw_rows.extend(resp)
        except ApiError as e:
            # Jika cabang ini belum diaktifkan fiturnya (403), teruskan error
            raise e
    else:
        # Jika cabang_id None (misal akun Pusat melihat semua cabang), query per cabang
        if not cabang_name_map:
            return []
        for cid in cabang_name_map.keys():
            params = {"cabang_id": cid, "limit": 500}
            if start_date:
                params["tanggal_awal"] = _iso(start_date)
            if end_date:
                params["tanggal_akhir"] = _iso(end_date)
            if jenis and str(jenis).lower() in ("pendapatan", "pengeluaran"):
                params["jenis"] = str(jenis).lower()
            try:
                resp = api_get("/pendapatan-pengeluaran", params=params)
                if resp:
                    raw_rows.extend(resp)
            except ApiError:
                # Abaikan cabang yang belum punya akses / 403 saat multi-cabang query
                continue

    items = []
    for r in raw_rows:
        # Structure: [id, cabang_id, tanggal, jenis, nama_pengeluaran, nominal, user_id, created_at, updated_at]
        eid, cid, tgl, jns, nama_pengeluaran, nom, *rest = r
        tgl_dt = to_date(tgl)

        # Filter Bulan & Tahun jika diberikan
        if bulan is not None and tgl_dt and tgl_dt.month != bulan:
            continue
        if tahun is not None and tgl_dt and tgl_dt.year != tahun:
            continue

        kat_extracted, ket_extracted = _parse_item_name(nama_pengeluaran)

        # Filter Kategori jika diberikan
        if kategori and kategori != "Semua" and kat_extracted.lower() != kategori.lower():
            continue

        cbg_nama = cabang_name_map.get(cid) or f"Cabang {cid}"

        # Filter Search keyword
        if search:
            s = search.lower().strip()
            nama_full = str(nama_pengeluaran or "").lower()
            cbg_str = cbg_nama.lower()
            if s not in nama_full and s not in cbg_str and s not in kat_extracted.lower() and s not in ket_extracted.lower():
                continue

        items.append({
            "id": eid,
            "cabang_id": cid,
            "nama_cabang": cbg_nama,
            "tanggal": tgl_dt or date.today(),
            "jenis": "Pendapatan" if str(jns).lower() == "pendapatan" else "Pengeluaran",
            "kategori": kat_extracted,
            "nominal": to_decimal(nom),
            "keterangan": ket_extracted or nama_pengeluaran or "-",
            "nota": "",
        })

    is_desc = (sort_order or "desc").lower() == "desc"
    items.sort(key=lambda x: (x["tanggal"], x["id"]), reverse=is_desc)
    return items


def add_transaksi_kas(cabang_id, nama_cabang, tanggal, jenis, kategori, nominal, keterangan, nota=""):
    """
    Menambahkan transaksi pendapatan/pengeluaran baru ke backend API (POST /pendapatan-pengeluaran).
    """
    nama_item = _format_item_name(kategori, keterangan)
    body = {
        "cabang_id": int(cabang_id),
        "tanggal": _iso(tanggal),
        "jenis": "pendapatan" if str(jenis).lower() == "pendapatan" else "pengeluaran",
        "nama_pengeluaran": nama_item[:150],
        "nominal": str(nominal),
    }
    resp = api_post("/pendapatan-pengeluaran", body)
    return resp.get("id") if resp else None


def update_transaksi_kas(transaksi_id, tanggal, jenis, kategori, nominal, keterangan, nota="", cabang_id=None, nama_cabang=None):
    """
    Memperbarui transaksi pendapatan/pengeluaran di backend API (PUT /pendapatan-pengeluaran/{id}).
    """
    nama_item = _format_item_name(kategori, keterangan)
    body = {
        "tanggal": _iso(tanggal),
        "jenis": "pendapatan" if str(jenis).lower() == "pendapatan" else "pengeluaran",
        "nama_pengeluaran": nama_item[:150],
        "nominal": str(nominal),
    }
    api_put(f"/pendapatan-pengeluaran/{transaksi_id}", body)
    return True


def delete_transaksi_kas(transaksi_id):
    """
    Menghapus transaksi pendapatan/pengeluaran dari backend API (DELETE /pendapatan-pengeluaran/{id}).
    """
    api_delete(f"/pendapatan-pengeluaran/{transaksi_id}")
    return True


def get_daily_summary(cabang_id, tanggal):
    """
    Mengambil summary harian kas dari backend API (GET /pendapatan-pengeluaran/summary/harian).
    """
    return api_get(
        "/pendapatan-pengeluaran/summary/harian",
        params={"cabang_id": cabang_id, "tanggal": _iso(tanggal)},
    )


def get_monthly_summary(cabang_id, bulan, tahun):
    """
    Mengambil summary bulanan kas dari backend API (GET /pendapatan-pengeluaran/summary/bulanan).
    """
    return api_get(
        "/pendapatan-pengeluaran/summary/bulanan",
        params={"cabang_id": cabang_id, "bulan": bulan, "tahun": tahun},
    )


# Alias untuk keseragaman penamaan dengan backend
get_entries = get_transaksi_kas
create_entry = add_transaksi_kas
update_entry = update_transaksi_kas
delete_entry = delete_transaksi_kas
