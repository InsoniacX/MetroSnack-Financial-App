import json
import os
from decimal import Decimal
from datetime import datetime, date

MOCK_FILE = os.path.join(os.path.dirname(__file__), "mock_pengambilan_balaraja.json")

LOKASI_BALARAJA_DEFAULT = [
    "Gudang Balaraja Pusat",
    "Gudang Balaraja Blok A",
    "Gudang Balaraja Blok B",
    "Depo Sentral Balaraja",
]

SATUAN_BALARAJA_DEFAULT = [
    "Bal",
    "Dus",
    "Pack",
    "Karton",
    "Kg",
    "Pcs",
]

KATEGORI_BALARAJA_DEFAULT = [
    "Keripik & Kerupuk",
    "Snack Tradisional",
    "Kacang & Pilus",
    "Kue Kering & Biskuit",
    "Grosir Repack",
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
        print(f"Error saving pengambilan balaraja mock: {ex}")


def get_pengambilan_balaraja(
    cabang_id=None,
    bulan=None,
    tahun=None,
    start_date=None,
    end_date=None,
    lokasi_gudang=None,
    kategori_barang=None,
    search=None,
    sort_order="desc",
):
    data = _load_raw_data()
    filtered = []

    for item in data:
        tgl_str = item.get("tanggal", "")
        try:
            tgl_dt = datetime.strptime(tgl_str, "%Y-%m-%d").date()
        except Exception:
            tgl_dt = None

        if cabang_id is not None and item.get("cabang_id") != cabang_id:
            continue
        if lokasi_gudang and lokasi_gudang != "Semua" and item.get("lokasi_gudang") != lokasi_gudang:
            continue
        if kategori_barang and kategori_barang != "Semua" and item.get("kategori_barang") != kategori_barang:
            continue

        if bulan is not None and tgl_dt and tgl_dt.month != bulan:
            continue
        if tahun is not None and tgl_dt and tgl_dt.year != tahun:
            continue

        if start_date and tgl_dt and tgl_dt < start_date:
            continue
        if end_date and tgl_dt and tgl_dt > end_date:
            continue

        if search:
            s = search.lower().strip()
            lokasi = str(item.get("lokasi_gudang", "")).lower()
            barang = str(item.get("nama_barang", "")).lower()
            sj = str(item.get("no_surat_jalan", "")).lower()
            drv = str(item.get("driver", "")).lower()
            ket = str(item.get("keterangan", "")).lower()
            if s not in lokasi and s not in barang and s not in sj and s not in drv and s not in ket:
                continue

        qty = float(item.get("qty", 0))
        harga_satuan = Decimal(str(item.get("harga_satuan", 0)))
        total_harga = Decimal(str(item.get("total_harga", qty * float(harga_satuan))))

        filtered.append({
            "id": item.get("id"),
            "tanggal": tgl_dt if tgl_dt else date.today(),
            "lokasi_gudang": item.get("lokasi_gudang", ""),
            "nama_barang": item.get("nama_barang", ""),
            "kategori_barang": item.get("kategori_barang", "Lain-lain"),
            "qty": qty,
            "satuan": item.get("satuan", "Bal"),
            "harga_satuan": harga_satuan,
            "total_harga": total_harga,
            "no_surat_jalan": item.get("no_surat_jalan", ""),
            "driver": item.get("driver", ""),
            "keterangan": item.get("keterangan", ""),
            "cabang_id": item.get("cabang_id", 1),
            "nama_cabang": item.get("nama_cabang", "Cabang"),
        })

    is_desc = (sort_order or "desc").lower() == "desc"
    filtered.sort(key=lambda x: (x["tanggal"], x["id"]), reverse=is_desc)
    return filtered


def add_pengambilan_balaraja(
    tanggal,
    lokasi_gudang,
    nama_barang,
    kategori_barang,
    qty,
    satuan,
    harga_satuan,
    no_surat_jalan="",
    driver="",
    keterangan="",
    cabang_id=1,
    nama_cabang="Cabang",
):
    data = _load_raw_data()
    next_id = max([item.get("id", 0) for item in data], default=0) + 1
    tgl_str = tanggal.isoformat() if hasattr(tanggal, "isoformat") else str(tanggal)

    q_val = float(qty)
    hs_val = float(harga_satuan)
    total_val = q_val * hs_val

    new_item = {
        "id": next_id,
        "tanggal": tgl_str,
        "lokasi_gudang": (lokasi_gudang or "Gudang Balaraja Pusat").strip(),
        "nama_barang": (nama_barang or "").strip(),
        "kategori_barang": kategori_barang or "Keripik & Kerupuk",
        "qty": q_val,
        "satuan": satuan or "Bal",
        "harga_satuan": hs_val,
        "total_harga": total_val,
        "no_surat_jalan": (no_surat_jalan or "").strip(),
        "driver": (driver or "").strip(),
        "keterangan": (keterangan or "").strip(),
        "cabang_id": cabang_id,
        "nama_cabang": nama_cabang or "Cabang",
    }
    data.append(new_item)
    _save_raw_data(data)
    return next_id


def update_pengambilan_balaraja(
    pengambilan_id,
    tanggal,
    lokasi_gudang,
    nama_barang,
    kategori_barang,
    qty,
    satuan,
    harga_satuan,
    no_surat_jalan="",
    driver="",
    keterangan="",
    cabang_id=None,
    nama_cabang=None,
):
    data = _load_raw_data()
    tgl_str = tanggal.isoformat() if hasattr(tanggal, "isoformat") else str(tanggal)
    q_val = float(qty)
    hs_val = float(harga_satuan)
    total_val = q_val * hs_val

    updated = False
    for item in data:
        if item.get("id") == pengambilan_id:
            item["tanggal"] = tgl_str
            item["lokasi_gudang"] = (lokasi_gudang or "").strip()
            item["nama_barang"] = (nama_barang or "").strip()
            item["kategori_barang"] = kategori_barang or "Keripik & Kerupuk"
            item["qty"] = q_val
            item["satuan"] = satuan or "Bal"
            item["harga_satuan"] = hs_val
            item["total_harga"] = total_val
            item["no_surat_jalan"] = (no_surat_jalan or "").strip()
            item["driver"] = (driver or "").strip()
            item["keterangan"] = (keterangan or "").strip()
            if cabang_id is not None:
                item["cabang_id"] = cabang_id
            if nama_cabang is not None:
                item["nama_cabang"] = nama_cabang
            updated = True
            break

    if updated:
        _save_raw_data(data)
    return updated


def delete_pengambilan_balaraja(pengambilan_id):
    data = _load_raw_data()
    data = [item for item in data if item.get("id") != pengambilan_id]
    _save_raw_data(data)
    return True


def get_akumulasi_bulanan_balaraja(tahun=None, cabang_id=None):
    """
    Menghitung akumulasi total pengambilan barang dari Balaraja per bulan dalam tahun berjalan.
    Mengembalikan ringkasan per bulan (1..12), total akumulasi tahunan, dan total qty.
    """
    if tahun is None:
        tahun = date.today().year

    data = _load_raw_data()
    monthly_data = {
        m: {"bulan": m, "total_nominal": Decimal(0), "total_qty": 0.0, "count": 0}
        for m in range(1, 13)
    }

    for item in data:
        tgl_str = item.get("tanggal", "")
        try:
            tgl_dt = datetime.strptime(tgl_str, "%Y-%m-%d").date()
        except Exception:
            continue

        if tgl_dt.year != tahun:
            continue
        if cabang_id is not None and item.get("cabang_id") != cabang_id:
            continue

        m = tgl_dt.month
        total_h = Decimal(str(item.get("total_harga", 0)))
        qty = float(item.get("qty", 0))

        monthly_data[m]["total_nominal"] += total_h
        monthly_data[m]["total_qty"] += qty
        monthly_data[m]["count"] += 1

    grand_total_nominal = sum(v["total_nominal"] for v in monthly_data.values())
    grand_total_qty = sum(v["total_qty"] for v in monthly_data.values())
    grand_total_count = sum(v["count"] for v in monthly_data.values())

    return {
        "tahun": tahun,
        "monthly": monthly_data,
        "grand_total_nominal": grand_total_nominal,
        "grand_total_qty": grand_total_qty,
        "grand_total_count": grand_total_count,
    }
