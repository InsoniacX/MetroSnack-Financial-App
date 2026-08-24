from fastapi import APIRouter, Depends, HTTPException
from auth.dependencies import get_current_user, assert_cabang_access
from models.schemas import InvoiceCreate, InvoiceUpdate, SisaBarangUpdate
from repositories import invoice_repo, folder_repo, transaksi_repo
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


@router.patch("/invoices/{invoice_id}/sisa-barang")
def update_sisa_barang(invoice_id: int, body: SisaBarangUpdate, user: dict = Depends(get_current_user)):
    """Item #3: update nilai Sisa Barang di Toko (input manual staff,
    dicek fisik tiap hari). Endpoint terpisah dari update_invoice supaya
    ringan -- staff cuma perlu kirim 1 angka ini tiap hari."""
    header = invoice_repo.get_invoice_header(invoice_id)
    if header is None:
        raise HTTPException(status_code=404, detail="Invoice tidak ditemukan")
    cabang_id = header[6]
    assert_cabang_access(user, cabang_id)
    invoice_repo.update_sisa_barang_manual(invoice_id, body.sisa_barang_manual)
    log_activity(user["id"], user["username"], "UPDATE", "invoice", invoice_id, f"Update Sisa Barang di Toko: {body.sisa_barang_manual}", cabang_id)
    return {"ok": True}


@router.get("/invoices/{invoice_id}/full")
def get_invoice_full(invoice_id: int, user: dict = Depends(get_current_user)):
    """Gabungan header + daftar transaksi dalam 1 request (bukan 2
    request terpisah), supaya halaman transaksi harian lebih cepat
    muncul -- terutama penting sekarang karena folder otomatis
    redirect ke sini (kebijakan 1 folder = 1 invoice)."""
    header = invoice_repo.get_invoice_header(invoice_id)
    if header is None:
        raise HTTPException(status_code=404, detail="Invoice tidak ditemukan")
    cabang_id = header[6]
    assert_cabang_access(user, cabang_id)
    transaksi = transaksi_repo.get_transaksi(invoice_id)
    return {"header": header, "transaksi": transaksi}


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
