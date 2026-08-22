from .http_client import api_get, api_post, api_put, api_delete
from ._convert import to_date, to_decimal


def _iso(value):
    return value.isoformat() if hasattr(value, "isoformat") else value


def get_transaksi(invoice_id):
    rows = api_get(f"/invoices/{invoice_id}/transaksi")
    result = []
    for r in rows:
        tid, tgl, mbarang, muang, lk, ket = r
        result.append((tid, to_date(tgl), to_decimal(mbarang), to_decimal(muang), to_decimal(lk), ket))
    return result


def add_transaksi(invoice_id, tanggal, masuk_barang, masuk_uang):
    body = {"tanggal": _iso(tanggal), "masuk_barang": str(masuk_barang), "masuk_uang": str(masuk_uang)}
    api_post(f"/invoices/{invoice_id}/transaksi", body)


def delete_transaksi(t_id):
    api_delete(f"/transaksi/{t_id}")


def update_transaksi(t_id, tanggal, masuk_barang, masuk_uang):
    body = {"tanggal": _iso(tanggal), "masuk_barang": str(masuk_barang), "masuk_uang": str(masuk_uang)}
    api_put(f"/transaksi/{t_id}", body)
