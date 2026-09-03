from decimal import Decimal
from datetime import datetime, date
from .http_client import api_get, api_post, api_put, api_patch, api_delete, ApiError
from ._convert import to_date, to_datetime, to_decimal
from .cabang_repo import get_active_cabang


def _iso(value):
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


# =========================================================================
# PERSONEL MASTER CRUD (/supir-kenek)
# =========================================================================
def get_personel_list(cabang_id=None, active_only=False, search=None):
    """
    Mengambil daftar master Supir & Kenek dari backend API.
    Jika cabang_id None (Pusat), query digabungkan untuk semua cabang aktif.
    """
    cabang_name_map = {}
    try:
        active_cabangs = get_active_cabang()
        cabang_name_map = {c[0]: c[1] for c in active_cabangs}
    except Exception:
        pass

    raw_rows = []
    if cabang_id is not None:
        params = {"cabang_id": cabang_id, "active_only": bool(active_only)}
        try:
            resp = api_get("/supir-kenek", params=params)
            if resp:
                raw_rows.extend(resp)
        except ApiError as e:
            raise e
    else:
        if not cabang_name_map:
            return []
        for cid in cabang_name_map.keys():
            params = {"cabang_id": cid, "active_only": bool(active_only)}
            try:
                resp = api_get("/supir-kenek", params=params)
                if resp:
                    raw_rows.extend(resp)
            except ApiError:
                continue

    results = []
    for r in raw_rows:
        # Structure: [id, cabang_id, nama, aktif, created_at, updated_at]
        pid, cid, nama, aktif, *rest = r
        if search:
            s = search.lower().strip()
            if s not in str(nama).lower():
                continue
        results.append({
            "id": pid,
            "cabang_id": cid,
            "nama_cabang": cabang_name_map.get(cid, f"Cabang {cid}"),
            "nama": nama,
            "aktif": bool(aktif),
            "status": "Aktif" if aktif else "Nonaktif",
            "created_at": to_datetime(rest[0]) if len(rest) > 0 else None,
            "updated_at": to_datetime(rest[1]) if len(rest) > 1 else None,
        })

    results.sort(key=lambda x: (not x["aktif"], x["nama"].lower()))
    return results


def add_personel(nama, cabang_id=1):
    """Menambahkan supir/kenek baru ke master data."""
    body = {
        "cabang_id": int(cabang_id),
        "nama": str(nama).strip(),
    }
    resp = api_post("/supir-kenek", json_body=body)
    return resp.get("id") if resp else None


def update_personel(personel_id, nama):
    """Mengubah nama supir/kenek."""
    body = {
        "nama": str(nama).strip(),
    }
    api_put(f"/supir-kenek/{personel_id}", json_body=body)
    return True


def set_personel_aktif(personel_id, aktif):
    """Mengubah status aktif/nonaktif supir/kenek."""
    api_patch(f"/supir-kenek/{personel_id}/aktif", params={"aktif": bool(aktif)})
    return True


# =========================================================================
# PENGELUARAN OPERASIONAL CRUD (/operasional-mobil)
# =========================================================================
def get_pengeluaran_supir_kenek(
    cabang_id=None,
    bulan=None,
    tahun=None,
    start_date=None,
    end_date=None,
    supir_id=None,
    kenek_id=None,
    personel_id=None,
    search=None,
    sort_order="desc",
):
    """
    Mengambil daftar catatan operasional mobil dari backend API.
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
        try:
            resp = api_get("/operasional-mobil", params=params)
            if resp:
                raw_rows.extend(resp)
        except ApiError as e:
            raise e
    else:
        if not cabang_name_map:
            return []
        for cid in cabang_name_map.keys():
            params = {"cabang_id": cid, "limit": 500}
            if start_date:
                params["tanggal_awal"] = _iso(start_date)
            if end_date:
                params["tanggal_akhir"] = _iso(end_date)
            try:
                resp = api_get("/operasional-mobil", params=params)
                if resp:
                    raw_rows.extend(resp)
            except ApiError:
                continue

    items = []
    for r in raw_rows:
        # Structure: [id, cabang_id, tanggal, supir_id, nama_supir, kenek_id, nama_kenek, uang_jalan, keterangan, user_id, username, created_at, updated_at]
        oid, cid, tgl, sid, nama_supir, kid, nama_kenek, uang_jalan, ket, uid, username, *rest = r
        tgl_dt = to_date(tgl)

        if bulan is not None and tgl_dt and tgl_dt.month != bulan:
            continue
        if tahun is not None and tgl_dt and tgl_dt.year != tahun:
            continue
        if start_date and tgl_dt and tgl_dt < (to_date(start_date) if isinstance(start_date, str) else start_date):
            continue
        if end_date and tgl_dt and tgl_dt > (to_date(end_date) if isinstance(end_date, str) else end_date):
            continue

        if supir_id is not None and sid != supir_id:
            continue
        if kenek_id is not None and kid != kenek_id:
            continue
        if personel_id is not None and sid != personel_id and kid != personel_id:
            continue

        if search:
            s = search.lower().strip()
            ns = str(nama_supir or "").lower()
            nk = str(nama_kenek or "").lower()
            keterangan_str = str(ket or "").lower()
            un = str(username or "").lower()
            if s not in ns and s not in nk and s not in keterangan_str and s not in un:
                continue

        nominal_dec = to_decimal(uang_jalan)
        items.append({
            "id": oid,
            "cabang_id": cid,
            "nama_cabang": cabang_name_map.get(cid, f"Cabang {cid}"),
            "tanggal": tgl_dt if tgl_dt else date.today(),
            "supir_id": sid,
            "nama_supir": nama_supir or "Supir",
            "nama_personel": nama_supir or "Supir",  # alias for backward compatibility
            "kenek_id": kid,
            "nama_kenek": nama_kenek or "-",
            "peran": f"Supir: {nama_supir}" + (f", Kenek: {nama_kenek}" if nama_kenek else ""),
            "uang_jalan": nominal_dec,
            "nominal": nominal_dec,  # alias for backward compatibility / rekap
            "keterangan": ket or "",
            "kategori_biaya": "Uang Jalan",  # alias
            "user_id": uid,
            "username": username or "",
            "created_at": to_datetime(rest[0]) if len(rest) > 0 else None,
            "updated_at": to_datetime(rest[1]) if len(rest) > 1 else None,
        })

    is_desc = (sort_order or "desc").lower() == "desc"
    items.sort(key=lambda x: (x["tanggal"], x["id"]), reverse=is_desc)
    return items


def add_pengeluaran_supir_kenek(
    tanggal,
    supir_id,
    kenek_id=None,
    uang_jalan=0,
    keterangan="",
    cabang_id=1,
    **kwargs,
):
    """Menambahkan catatan operasional mobil baru."""
    body = {
        "tanggal": _iso(tanggal),
        "supir_id": int(supir_id),
        "kenek_id": int(kenek_id) if kenek_id and int(kenek_id) > 0 else None,
        "uang_jalan": float(uang_jalan),
        "keterangan": (keterangan or "").strip() or None,
        "cabang_id": int(cabang_id),
    }
    resp = api_post("/operasional-mobil", json_body=body)
    return resp.get("id") if resp else None


def update_pengeluaran_supir_kenek(
    pengeluaran_id,
    tanggal,
    supir_id,
    kenek_id=None,
    uang_jalan=0,
    keterangan="",
    **kwargs,
):
    """Mengubah data catatan operasional mobil."""
    body = {
        "tanggal": _iso(tanggal),
        "supir_id": int(supir_id),
        "kenek_id": int(kenek_id) if kenek_id and int(kenek_id) > 0 else None,
        "uang_jalan": float(uang_jalan),
        "keterangan": (keterangan or "").strip() or None,
    }
    api_put(f"/operasional-mobil/{pengeluaran_id}", json_body=body)
    return True


def delete_pengeluaran_supir_kenek(pengeluaran_id):
    """Menghapus catatan operasional mobil."""
    api_delete(f"/operasional-mobil/{pengeluaran_id}")
    return True


def get_rekap_supir_kenek_bulanan(bulan, tahun, cabang_id=None):
    """Mengembalikan total nominal dan breakdown biaya operasional supir & kenek bulanan."""
    items = get_pengeluaran_supir_kenek(cabang_id=cabang_id, bulan=bulan, tahun=tahun)
    total_biaya = sum((it["nominal"] for it in items), Decimal(0))

    supir_totals = {}
    kenek_totals = {}
    for it in items:
        s_name = it["nama_supir"]
        supir_totals[s_name] = supir_totals.get(s_name, Decimal(0)) + it["nominal"]
        if it.get("nama_kenek") and it["nama_kenek"] != "-":
            k_name = it["nama_kenek"]
            kenek_totals[k_name] = kenek_totals.get(k_name, Decimal(0)) + it["nominal"]

    return {
        "items": items,
        "total": total_biaya,
        "count": len(items),
        "supir_totals": supir_totals,
        "kenek_totals": kenek_totals,
        "personel_totals": supir_totals,  # alias
    }

