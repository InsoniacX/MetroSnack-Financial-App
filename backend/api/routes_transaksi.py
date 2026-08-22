from fastapi import APIRouter, Depends, HTTPException
from auth.dependencies import get_current_user, assert_cabang_access
from models.schemas import TransaksiCreate, TransaksiUpdate
from repositories import transaksi_repo, invoice_repo
from repositories.activity_repo import log_activity

router = APIRouter(tags=["transaksi"])


def _assert_invoice_access(user, invoice_id):
    header = invoice_repo.get_invoice_header(invoice_id)
    if header is None:
        raise HTTPException(status_code=404, detail="Invoice tidak ditemukan")
    cabang_id = header[6]
    assert_cabang_access(user, cabang_id)


def _assert_transaksi_access(user, transaksi_id):
    """Cek isolasi cabang untuk transaksi lewat invoice -> folder_bulan -> cabang.
    Sebelumnya ini belum dicek (ditandai TODO keamanan) -- sekarang sudah."""
    cabang_id = transaksi_repo.get_transaksi_cabang_id(transaksi_id)
    if cabang_id is None:
        raise HTTPException(status_code=404, detail="Transaksi tidak ditemukan")
    assert_cabang_access(user, cabang_id)


@router.get("/invoices/{invoice_id}/transaksi")
def list_transaksi(invoice_id: int, user: dict = Depends(get_current_user)):
    _assert_invoice_access(user, invoice_id)
    return transaksi_repo.get_transaksi(invoice_id)


@router.post("/invoices/{invoice_id}/transaksi")
def add_transaksi(invoice_id: int, body: TransaksiCreate, user: dict = Depends(get_current_user)):
    _assert_invoice_access(user, invoice_id)
    transaksi_repo.add_transaksi(invoice_id, body.tanggal, body.masuk_barang, body.masuk_uang)
    log_activity(user["id"], user["username"], "CREATE", "transaksi_harian", invoice_id, None, None)
    return {"ok": True}


@router.put("/transaksi/{transaksi_id}")
def update_transaksi(transaksi_id: int, body: TransaksiUpdate, user: dict = Depends(get_current_user)):
    _assert_transaksi_access(user, transaksi_id)
    transaksi_repo.update_transaksi(transaksi_id, body.tanggal, body.masuk_barang, body.masuk_uang)
    log_activity(user["id"], user["username"], "UPDATE", "transaksi_harian", transaksi_id, None, None)
    return {"ok": True}


@router.delete("/transaksi/{transaksi_id}")
def delete_transaksi(transaksi_id: int, user: dict = Depends(get_current_user)):
    _assert_transaksi_access(user, transaksi_id)
    transaksi_repo.delete_transaksi(transaksi_id)
    log_activity(user["id"], user["username"], "DELETE", "transaksi_harian", transaksi_id, None, None)
    return {"ok": True}
