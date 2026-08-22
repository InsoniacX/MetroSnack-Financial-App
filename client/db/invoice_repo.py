from .http_client import api_get, api_post, api_put, api_delete, ApiError
from ._convert import to_date, to_decimal


def get_invoices(folder_id):
    rows = api_get(f"/folders/{folder_id}/invoices")
    result = []
    for r in rows:
        iid, no_laporan, tgl_dibuat, tgl_laporan, invoice_bon, total_omzet, total_barang = r
        result.append((
            iid, no_laporan, to_date(tgl_dibuat), to_date(tgl_laporan),
            to_decimal(invoice_bon), to_decimal(total_omzet), to_decimal(total_barang),
        ))
    return result


def _iso(value):
    return value.isoformat() if hasattr(value, "isoformat") else value


def create_invoice(folder_id, no_laporan, tanggal_dibuat, tanggal_laporan, invoice_bon, user_id):
    body = {
        "no_laporan": no_laporan,
        "tanggal_dibuat": _iso(tanggal_dibuat),
        "tanggal_laporan": _iso(tanggal_laporan),
        "invoice_bon": str(invoice_bon),
    }
    resp = api_post(f"/folders/{folder_id}/invoices", body)
    return resp["id"]


def delete_invoice(invoice_id):
    api_delete(f"/invoices/{invoice_id}")


def get_invoice_header(invoice_id):
    try:
        row = api_get(f"/invoices/{invoice_id}")
    except ApiError as e:
        if e.status_code == 404:
            return None
        raise
    if row is None:
        return None
    iid, no_laporan, tgl_dibuat, tgl_laporan, invoice_bon, folder_bulan_id, cabang_id = row
    return (iid, no_laporan, to_date(tgl_dibuat), to_date(tgl_laporan), to_decimal(invoice_bon), folder_bulan_id, cabang_id)


def update_invoice(invoice_id, no_laporan, tanggal_dibuat, tanggal_laporan, invoice_bon):
    body = {
        "no_laporan": no_laporan,
        "tanggal_dibuat": _iso(tanggal_dibuat),
        "tanggal_laporan": _iso(tanggal_laporan),
        "invoice_bon": str(invoice_bon),
    }
    api_put(f"/invoices/{invoice_id}", body)
