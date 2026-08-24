from .http_client import api_get, api_post, api_delete, ApiError
from ._convert import to_decimal


def get_dashboard_summary(cabang_id=None):
    """Kembalikan dict dengan key lama (omzet, barang, laba_bersih) SUPAYA
    KODE VIEW LAMA TETAP JALAN, plus key baru 'sisa_hutang' (dari formula
    CONFIRMED di backend) untuk card Total Hutang yang baru ditambahkan."""
    params = {}
    if cabang_id is not None:
        params["cabang_id"] = cabang_id
    resp = api_get("/dashboard/summary", params=params)
    omzet = to_decimal(resp["masuk_uang"])
    barang = to_decimal(resp["masuk_barang"])
    return {
        "omzet": omzet,
        "barang": barang,
        "laba_bersih": omzet - barang,
        "sisa_hutang": to_decimal(resp["sisa_hutang"]),
    }


def get_cabang_breakdown():
    rows = api_get("/dashboard/cabang-breakdown")
    return [
        (r["cabang_id"], r["nama_cabang"], to_decimal(r["masuk_uang"]), to_decimal(r["masuk_barang"]))
        for r in rows
    ]


def get_cabang_summary():
    rows = api_get("/dashboard/cabang-summary")
    return [tuple(r) for r in rows]


def get_monthly_trend(cabang_id=None, limit_months=6):
    params = {"limit_months": limit_months}
    if cabang_id is not None:
        params["cabang_id"] = cabang_id
    rows = api_get("/dashboard/monthly-trend", params=params)
    result = []
    for r in rows:
        omzet = to_decimal(r["masuk_uang"])
        barang = to_decimal(r["masuk_barang"])
        result.append((r["folder_id"], r["nama_folder"], r["bulan"], r["tahun"], omzet, omzet - barang))
    return result


def get_folders(cabang_id=None):
    params = {}
    if cabang_id is not None:
        params["cabang_id"] = cabang_id
    rows = api_get("/folders", params=params)
    result = []
    for r in rows:
        fid, nama_folder, bulan, tahun, nama_cabang, total_invoice, total_modal, total_omzet, total_barang = r
        laba_bersih = to_decimal(total_omzet) - to_decimal(total_barang)
        result.append((fid, nama_folder, bulan, tahun, nama_cabang, total_invoice, laba_bersih))
    return result


def create_folder(bulan, tahun, cabang_id, user_id):
    resp = api_post("/folders", {"bulan": bulan, "tahun": tahun, "cabang_id": cabang_id})
    return resp["id"]


def get_invoice_ids(folder_id):
    """Query RINGAN -- cuma id invoice, dipakai main.py untuk cek cepat
    'folder ini punya berapa invoice' sebelum redirect ke halaman
    transaksi (jauh lebih cepat daripada get_invoices() yang hitung
    agregat SUM masuk_uang/masuk_barang segala)."""
    return api_get(f"/folders/{folder_id}/invoice-ids")


def get_folder_header(folder_id):
    try:
        row = api_get(f"/folders/{folder_id}")
    except ApiError as e:
        if e.status_code == 404:
            return None
        raise
    return tuple(row) if row is not None else None


def delete_folder(folder_id):
    api_delete(f"/folders/{folder_id}")
