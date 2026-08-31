import json
import os
from decimal import Decimal
from datetime import datetime, date

MOCK_FILE = os.path.join(os.path.dirname(__file__), "mock_supir_kenek.json")

KATEGORI_BIAYA_KENEK = [
    "Uang Jalan / Saku",
    "BBM / Bensin",
    "Tol & Parkir",
    "Makan & Minum",
    "Bongkar Muat",
    "Lembur / Bonus Trip",
    "Perbaikan Darurat",
    "Lain-lain",
]

PERAN_OPTIONS = ["Supir", "Kenek", "Supir & Kenek"]


def _load_raw():
    if not os.path.exists(MOCK_FILE):
        return {"personel": [], "pengeluaran": []}
    try:
        with open(MOCK_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return {"personel": [], "pengeluaran": data}
            return data
    except Exception:
        return {"personel": [], "pengeluaran": []}


def _save_raw(data):
    try:
        with open(MOCK_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as ex:
        print(f"Error saving supir kenek mock: {ex}")


# =========================================================================
# PERSONEL MASTER CRUD
# =========================================================================
def get_personel_list(cabang_id=None, status=None, search=None):
    raw = _load_raw()
    items = raw.get("personel", [])
    results = []
    for it in items:
        if cabang_id is not None and it.get("cabang_id") != cabang_id:
            continue
        if status and status != "Semua" and it.get("status") != status:
            continue
        if search:
            s = search.lower().strip()
            nama = str(it.get("nama", "")).lower()
            peran = str(it.get("peran", "")).lower()
            armada = str(it.get("armada", "")).lower()
            no_telp = str(it.get("no_telp", "")).lower()
            if s not in nama and s not in peran and s not in armada and s not in no_telp:
                continue
        results.append({
            "id": it.get("id"),
            "nama": it.get("nama", ""),
            "peran": it.get("peran", "Supir"),
            "no_telp": it.get("no_telp", ""),
            "armada": it.get("armada", ""),
            "cabang_id": it.get("cabang_id", 1),
            "nama_cabang": it.get("nama_cabang", "Cabang"),
            "status": it.get("status", "Aktif"),
        })
    results.sort(key=lambda x: x["nama"].lower())
    return results


def add_personel(nama, peran, no_telp="", armada="", cabang_id=1, nama_cabang="Cabang", status="Aktif"):
    raw = _load_raw()
    items = raw.setdefault("personel", [])
    next_id = max([it.get("id", 0) for it in items], default=0) + 1
    new_p = {
        "id": next_id,
        "nama": nama.strip(),
        "peran": peran,
        "no_telp": (no_telp or "").strip(),
        "armada": (armada or "").strip(),
        "cabang_id": cabang_id,
        "nama_cabang": nama_cabang or "Cabang",
        "status": status or "Aktif",
    }
    items.append(new_p)
    _save_raw(raw)
    return next_id


def update_personel(personel_id, nama, peran, no_telp="", armada="", cabang_id=None, nama_cabang=None, status=None):
    raw = _load_raw()
    items = raw.setdefault("personel", [])
    updated = False
    for it in items:
        if it.get("id") == personel_id:
            it["nama"] = nama.strip()
            it["peran"] = peran
            it["no_telp"] = (no_telp or "").strip()
            it["armada"] = (armada or "").strip()
            if cabang_id is not None:
                it["cabang_id"] = cabang_id
            if nama_cabang is not None:
                it["nama_cabang"] = nama_cabang
            if status is not None:
                it["status"] = status
            updated = True
            break
    if updated:
        _save_raw(raw)
    return updated


def delete_personel(personel_id):
    raw = _load_raw()
    raw["personel"] = [it for it in raw.get("personel", []) if it.get("id") != personel_id]
    _save_raw(raw)
    return True


# =========================================================================
# PENGELUARAN OPERASIONAL CRUD
# =========================================================================
def get_pengeluaran_supir_kenek(
    cabang_id=None,
    bulan=None,
    tahun=None,
    start_date=None,
    end_date=None,
    personel_id=None,
    kategori=None,
    search=None,
    sort_order="desc",
):
    raw = _load_raw()
    items = raw.get("pengeluaran", [])
    filtered = []

    for it in items:
        tgl_str = it.get("tanggal", "")
        try:
            tgl_dt = datetime.strptime(tgl_str, "%Y-%m-%d").date()
        except Exception:
            tgl_dt = None

        if cabang_id is not None and it.get("cabang_id") != cabang_id:
            continue
        if personel_id is not None and it.get("personel_id") != personel_id:
            continue
        if kategori and kategori != "Semua" and it.get("kategori_biaya") != kategori:
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
            ket = str(it.get("keterangan", "")).lower()
            nota = str(it.get("nota", "")).lower()
            nama = str(it.get("nama_personel", "")).lower()
            kat = str(it.get("kategori_biaya", "")).lower()
            if s not in ket and s not in nota and s not in nama and s not in kat:
                continue

        filtered.append({
            "id": it.get("id"),
            "tanggal": tgl_dt if tgl_dt else date.today(),
            "personel_id": it.get("personel_id"),
            "nama_personel": it.get("nama_personel", "Supir/Kenek"),
            "peran": it.get("peran", "Supir"),
            "kategori_biaya": it.get("kategori_biaya", "Lain-lain"),
            "nominal": Decimal(str(it.get("nominal", 0))),
            "keterangan": it.get("keterangan", ""),
            "nota": it.get("nota", ""),
            "cabang_id": it.get("cabang_id", 1),
            "nama_cabang": it.get("nama_cabang", "Cabang"),
        })

    is_desc = (sort_order or "desc").lower() == "desc"
    filtered.sort(key=lambda x: (x["tanggal"], x["id"]), reverse=is_desc)
    return filtered


def add_pengeluaran_supir_kenek(
    tanggal,
    personel_id,
    nama_personel,
    peran,
    kategori_biaya,
    nominal,
    keterangan,
    nota="",
    cabang_id=1,
    nama_cabang="Cabang",
):
    raw = _load_raw()
    items = raw.setdefault("pengeluaran", [])
    next_id = max([it.get("id", 0) for it in items], default=0) + 1

    tgl_str = tanggal.isoformat() if hasattr(tanggal, "isoformat") else str(tanggal)
    new_item = {
        "id": next_id,
        "tanggal": tgl_str,
        "personel_id": personel_id,
        "nama_personel": nama_personel or "Supir/Kenek",
        "peran": peran or "Supir",
        "kategori_biaya": kategori_biaya or "Lain-lain",
        "nominal": float(nominal),
        "keterangan": keterangan or "",
        "nota": (nota or "").strip(),
        "cabang_id": cabang_id,
        "nama_cabang": nama_cabang or "Cabang",
    }
    items.append(new_item)
    _save_raw(raw)
    return next_id


def update_pengeluaran_supir_kenek(
    pengeluaran_id,
    tanggal,
    personel_id,
    nama_personel,
    peran,
    kategori_biaya,
    nominal,
    keterangan,
    nota="",
    cabang_id=None,
    nama_cabang=None,
):
    raw = _load_raw()
    items = raw.setdefault("pengeluaran", [])
    tgl_str = tanggal.isoformat() if hasattr(tanggal, "isoformat") else str(tanggal)

    updated = False
    for it in items:
        if it.get("id") == pengeluaran_id:
            it["tanggal"] = tgl_str
            it["personel_id"] = personel_id
            it["nama_personel"] = nama_personel
            it["peran"] = peran
            it["kategori_biaya"] = kategori_biaya
            it["nominal"] = float(nominal)
            it["keterangan"] = keterangan or ""
            it["nota"] = (nota or "").strip()
            if cabang_id is not None:
                it["cabang_id"] = cabang_id
            if nama_cabang is not None:
                it["nama_cabang"] = nama_cabang
            updated = True
            break

    if updated:
        _save_raw(raw)
    return updated


def delete_pengeluaran_supir_kenek(pengeluaran_id):
    raw = _load_raw()
    raw["pengeluaran"] = [it for it in raw.get("pengeluaran", []) if it.get("id") != pengeluaran_id]
    _save_raw(raw)
    return True


def get_rekap_supir_kenek_bulanan(bulan, tahun, cabang_id=None):
    """Mengembalikan total nominal dan breakdown biaya kenek/supir untuk bulan tertentu."""
    items = get_pengeluaran_supir_kenek(cabang_id=cabang_id, bulan=bulan, tahun=tahun)
    total_biaya = sum(it["nominal"] for it in items)
    
    kategori_totals = {}
    for k in KATEGORI_BIAYA_KENEK:
        kategori_totals[k] = Decimal(0)
    for it in items:
        kat = it["kategori_biaya"]
        kategori_totals[kat] = kategori_totals.get(kat, Decimal(0)) + it["nominal"]

    personel_totals = {}
    for it in items:
        p_name = it["nama_personel"]
        personel_totals[p_name] = personel_totals.get(p_name, Decimal(0)) + it["nominal"]

    return {
        "items": items,
        "total": total_biaya,
        "count": len(items),
        "kategori_totals": kategori_totals,
        "personel_totals": personel_totals,
    }
