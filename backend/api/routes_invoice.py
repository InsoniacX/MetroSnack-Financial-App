from fastapi import APIRouter, Depends, HTTPException
from auth.dependencies import get_current_user, assert_cabang_access
from models.schemas import InvoiceCreate, InvoiceUpdate
from repositories import invoice_repo, folder_repo
from repositories.activity_repo import log_activity
from services.finance_service import hitung_sisa_hutang

router = APIRouter(tags=["invoices"])


def _assert_folder_access(user, folder_id):
    header = folder_repo.get_folder_header(folder_id)
    if header is None:
        raise HTTPException(status_code=404, detail="Folder tidak ditemukan")
    _, _, cabang_id, _ = header
    assert_cabang_access(user, cabang_id)
    return cabang_id


@router.get("/folders/{folder_id}/invoices")
def list_invoices(folder_id: int, user: dict = Depends(get_current_user)):
    _assert_folder_access(user, folder_id)
    return invoice_repo.get_invoices(folder_id)


@router.post("/folders/{folder_id}/invoices")
def create_invoice(folder_id: int, body: InvoiceCreate, user: dict = Depends(get_current_user)):
    _assert_folder_access(user, folder_id)
    new_id = invoice_repo.create_invoice(
        folder_id, body.no_laporan, body.tanggal_dibuat, body.tanggal_laporan,
        body.invoice_bon, user["id"],
    )
    log_activity(user["id"], user["username"], "CREATE", "invoice", new_id, body.no_laporan, None)
    return {"id": new_id}


@router.get("/invoices/{invoice_id}")
def get_invoice(invoice_id: int, user: dict = Depends(get_current_user)):
    # header: id, no_laporan, tanggal_dibuat, tanggal_laporan, invoice_bon, folder_bulan_id, cabang_id
    header = invoice_repo.get_invoice_header(invoice_id)
    if header is None:
        raise HTTPException(status_code=404, detail="Invoice tidak ditemukan")
    cabang_id = header[6]
    assert_cabang_access(user, cabang_id)
    return header


@router.put("/invoices/{invoice_id}")
def update_invoice(invoice_id: int, body: InvoiceUpdate, user: dict = Depends(get_current_user)):
    header = invoice_repo.get_invoice_header(invoice_id)
    if header is None:
        raise HTTPException(status_code=404, detail="Invoice tidak ditemukan")
    cabang_id = header[6]
    assert_cabang_access(user, cabang_id)
    invoice_repo.update_invoice(
        invoice_id, body.no_laporan, body.tanggal_dibuat, body.tanggal_laporan, body.invoice_bon,
    )
    log_activity(user["id"], user["username"], "UPDATE", "invoice", invoice_id, body.no_laporan, None)
    return {"ok": True}


@router.delete("/invoices/{invoice_id}")
def delete_invoice(invoice_id: int, user: dict = Depends(get_current_user)):
    header = invoice_repo.get_invoice_header(invoice_id)
    if header is None:
        raise HTTPException(status_code=404, detail="Invoice tidak ditemukan")
    cabang_id = header[6]
    assert_cabang_access(user, cabang_id)
    invoice_repo.delete_invoice(invoice_id)
    log_activity(user["id"], user["username"], "DELETE", "invoice", invoice_id, None, None)
    return {"ok": True}


@router.get("/invoices/{invoice_id}/sisa-hutang")
def get_sisa_hutang(invoice_id: int, user: dict = Depends(get_current_user)):
    """
    CANDIDATE - lihat services/finance_service.py. Endpoint ini
    mengembalikan breakdown lengkap (bukan cuma angka akhir) supaya
    gampang dicocokkan ke ledger saat proses verifikasi.
    """
    header = invoice_repo.get_invoice_header(invoice_id)
    if header is None:
        raise HTTPException(status_code=404, detail="Invoice tidak ditemukan")
    cabang_id = header[6]
    assert_cabang_access(user, cabang_id)

    totals = invoice_repo.get_invoice_totals(invoice_id)
    if totals is None:
        raise HTTPException(status_code=404, detail="Data transaksi invoice tidak ditemukan")
    modal_pusat, masuk_uang, masuk_barang = totals
    return hitung_sisa_hutang(modal_pusat, masuk_uang, masuk_barang)
