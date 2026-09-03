from decimal import Decimal
from datetime import datetime, date
from .http_client import api_get, api_post, api_put, api_delete, ApiError
from ._convert import to_date, to_datetime, to_decimal
from .cabang_repo import get_active_cabang, get_all_cabang


def _iso(value):
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def get_pengambilan_pabrik(
    cabang_id=None,
    bulan=None,
    tahun=None,
    start_date=None,
    end_date=None,
    search=None,
    sort_order="desc",
    **kwargs,
):
    """
    Mengambil data pengambilan kas pabrik dari backend REST API.
    Jika cabang_id None (Pusat), data diambil dari semua cabang.
    """
    cabang_name_map = {}
    try:
        all_cabangs = get_all_cabang()
        cabang_name_map = {c[0]: c[1] for c in all_cabangs}
    except Exception:
        pass
    if not cabang_name_map:
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
            resp = api_get("/pengambilan-kas/pabrik", params=params)
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
                resp = api_get("/pengambilan-kas/pabrik", params=params)
                if resp:
                    raw_rows.extend(resp)
            except ApiError:
                continue

    items = []
    for r in raw_rows:
        # Structure: [id, cabang_id, tanggal, keterangan, nominal, user_id, username, created_at, updated_at]
        eid, cid, tgl, ket, nom, uid, username, *rest = r
        tgl_dt = to_date(tgl)

        if bulan is not None and tgl_dt and tgl_dt.month != bulan:
            continue
        if tahun is not None and tgl_dt and tgl_dt.year != tahun:
            continue
        if start_date and tgl_dt and tgl_dt < (to_date(start_date) if isinstance(start_date, str) else start_date):
            continue
        if end_date and tgl_dt and tgl_dt > (to_date(end_date) if isinstance(end_date, str) else end_date):
            continue

        if search:
            s = search.lower().strip()
            ket_str = str(ket or "").lower()
            un = str(username or "").lower()
            if s not in ket_str and s not in un:
                continue

        nom_dec = to_decimal(nom)
        items.append({
            "id": eid,
            "cabang_id": cid,
            "nama_cabang": cabang_name_map.get(cid, f"Cabang {cid}"),
            "tanggal": tgl_dt if tgl_dt else date.today(),
            "keterangan": ket or "",
            "nama_pabrik": ket or "Pabrik",  # alias for backward compat
            "nama_barang": ket or "",         # alias for backward compat
            "qty": Decimal(1),               # alias for backward compat
            "satuan": "Trx",                  # alias for backward compat
            "harga_satuan": nom_dec,         # alias for backward compat
            "total_harga": nom_dec,          # alias for backward compat
            "nominal": nom_dec,
            "user_id": uid,
            "username": username or "",
            "created_at": to_datetime(rest[0]) if len(rest) > 0 else None,
            "updated_at": to_datetime(rest[1]) if len(rest) > 1 else None,
        })

    is_desc = (sort_order or "desc").lower() == "desc"
    items.sort(key=lambda x: (x["tanggal"], x["id"]), reverse=is_desc)
    return items


def add_pengambilan_pabrik(
    tanggal,
    keterangan,
    nominal,
    cabang_id=1,
    **kwargs,
):
    """Menambahkan catatan pengambilan kas pabrik baru."""
    body = {
        "cabang_id": int(cabang_id),
        "tanggal": _iso(tanggal),
        "keterangan": str(keterangan).strip(),
        "nominal": float(nominal),
    }
    resp = api_post("/pengambilan-kas/pabrik", json_body=body)
    return resp.get("id") if resp else None


def update_pengambilan_pabrik(
    entry_id,
    tanggal,
    keterangan,
    nominal,
    **kwargs,
):
    """Mengubah catatan pengambilan kas pabrik."""
    body = {
        "tanggal": _iso(tanggal),
        "keterangan": str(keterangan).strip(),
        "nominal": float(nominal),
    }
    api_put(f"/pengambilan-kas/pabrik/{entry_id}", json_body=body)
    return True


def delete_pengambilan_pabrik(entry_id):
    """Menghapus catatan pengambilan kas pabrik."""
    api_delete(f"/pengambilan-kas/pabrik/{entry_id}")
    return True


def get_akumulasi_bulanan_pabrik(bulan=None, tahun=None, cabang_id=None):
    """Mengembalikan rekap total biaya pengambilan pabrik pada bulan/tahun tertentu."""
    items = get_pengambilan_pabrik(cabang_id=cabang_id, bulan=bulan, tahun=tahun)
    total_biaya = sum((it["nominal"] for it in items), Decimal(0))
    return {
        "items": items,
        "total": total_biaya,
        "count": len(items),
    }

