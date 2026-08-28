import json
import os
from decimal import Decimal
from datetime import datetime, date

MOCK_FILE = os.path.join(os.path.dirname(__file__), "mock_pendapatan_pengeluaran.json")

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


def _load_raw_data():
    if not os.path.exists(MOCK_FILE):
        return []
    try:
        with open(MOCK_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _save_raw_data(data):
    try:
        with open(MOCK_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as ex:
        print(f"Error saving mock data: {ex}")


def get_transaksi_kas(cabang_id=None, bulan=None, tahun=None, start_date=None, end_date=None, jenis=None, kategori=None, search=None):
    """Mengambil daftar transaksi kas dari JSON mockup dengan filter lengkap."""
    data = _load_raw_data()
    filtered = []

    for item in data:
        tgl_str = item.get("tanggal", "")
        try:
            tgl_dt = datetime.strptime(tgl_str, "%Y-%m-%d").date()
        except Exception:
            tgl_dt = None

        # Filter Cabang (jika bukan pusat atau jika filter cabang dipilih)
        if cabang_id is not None and item.get("cabang_id") != cabang_id:
            continue

        # Filter Jenis (Pendapatan / Pengeluaran)
        if jenis and jenis != "Semua" and item.get("jenis") != jenis:
            continue

        # Filter Kategori
        if kategori and kategori != "Semua" and item.get("kategori") != kategori:
            continue

        # Filter Periode: Bulan & Tahun
        if bulan is not None and tgl_dt:
            if tgl_dt.month != bulan:
                continue
        if tahun is not None and tgl_dt:
            if tgl_dt.year != tahun:
                continue

        # Filter Periode: Rentang Tanggal (start_date s/d end_date)
        if start_date and tgl_dt:
            if tgl_dt < start_date:
                continue
        if end_date and tgl_dt:
            if tgl_dt > end_date:
                continue

        # Filter Search text
        if search:
            s = search.lower().strip()
            ket = str(item.get("keterangan", "")).lower()
            nota = str(item.get("nota", "")).lower()
            kat = str(item.get("kategori", "")).lower()
            cbg = str(item.get("nama_cabang", "")).lower()
            if s not in ket and s not in nota and s not in kat and s not in cbg:
                continue

        filtered.append({
            "id": item.get("id"),
            "cabang_id": item.get("cabang_id"),
            "nama_cabang": item.get("nama_cabang", "Cabang"),
            "tanggal": tgl_dt if tgl_dt else date.today(),
            "jenis": item.get("jenis", "Pendapatan"),
            "kategori": item.get("kategori", "Lain-lain"),
            "nominal": Decimal(str(item.get("nominal", 0))),
            "keterangan": item.get("keterangan", ""),
            "nota": item.get("nota", ""),
        })

    # Urutkan berdasarkan tanggal terbaru lalu ID terbesar
    filtered.sort(key=lambda x: (x["tanggal"], x["id"]), reverse=True)
    return filtered


def add_transaksi_kas(cabang_id, nama_cabang, tanggal, jenis, kategori, nominal, keterangan, nota=""):
    """Menambahkan transaksi baru ke data mockup JSON."""
    data = _load_raw_data()
    next_id = max([item.get("id", 0) for item in data], default=0) + 1

    tgl_str = tanggal.isoformat() if hasattr(tanggal, "isoformat") else str(tanggal)
    new_item = {
        "id": next_id,
        "cabang_id": cabang_id,
        "nama_cabang": nama_cabang or "Cabang",
        "tanggal": tgl_str,
        "jenis": jenis,
        "kategori": kategori,
        "nominal": float(nominal),
        "keterangan": keterangan or "",
        "nota": (nota or "").strip(),
    }
    data.append(new_item)
    _save_raw_data(data)
    return next_id


def update_transaksi_kas(transaksi_id, tanggal, jenis, kategori, nominal, keterangan, nota="", cabang_id=None, nama_cabang=None):
    """Memperbarui transaksi yang ada di data mockup JSON."""
    data = _load_raw_data()
    tgl_str = tanggal.isoformat() if hasattr(tanggal, "isoformat") else str(tanggal)

    updated = False
    for item in data:
        if item.get("id") == transaksi_id:
            item["tanggal"] = tgl_str
            item["jenis"] = jenis
            item["kategori"] = kategori
            item["nominal"] = float(nominal)
            item["keterangan"] = keterangan or ""
            item["nota"] = (nota or "").strip()
            if cabang_id is not None:
                item["cabang_id"] = cabang_id
            if nama_cabang:
                item["nama_cabang"] = nama_cabang
            updated = True
            break

    if updated:
        _save_raw_data(data)
    return updated


def delete_transaksi_kas(transaksi_id):
    """Menghapus transaksi dari data mockup JSON."""
    data = _load_raw_data()
    data = [item for item in data if item.get("id") != transaksi_id]
    _save_raw_data(data)
    return True
