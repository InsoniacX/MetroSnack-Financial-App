from typing import Literal

from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query
from auth.dependencies import get_current_user, assert_cabang_access
from models.schemas import PendapatanPengeluaranCreate, PendapatanPengeluaranUpdate
from repositories import pendapatan_pengeluaran_repo as repo
from repositories.activity_repo import log_activity
from repositories import cabang_repo
from config import PENDAPATAN_PENGELUARAN_ALLOWED_CABANG

router = APIRouter(prefix="/pendapatan-pengeluaran", tags=["pendapatan-pengeluaran"])


_ALLOWED_CABANG = {
    nama.strip().casefold()
    for nama in PENDAPATAN_PENGELUARAN_ALLOWED_CABANG
    if nama.strip()
}

def _assert_entry_access(user, entry_id):
    header = repo.get_entry_header(entry_id)
    if header is None:
        raise HTTPException(status_code=404, detail="Data tidak ditemukan")
    _, cabang_id = header
    assert_cabang_access(user, cabang_id)
    return cabang_id


@router.get("")
def list_entries(
    cabang_id: int,
    tanggal_awal: date | None = None,
    tanggal_akhir: date | None = None,
    jenis: str | None = None,
    user: dict = Depends(get_current_user),
):
    assert_cabang_access(user, cabang_id)
    return repo.get_entries(cabang_id, tanggal_awal, tanggal_akhir, jenis)


@router.post("")
def create_entry(body: PendapatanPengeluaranCreate, user: dict = Depends(get_current_user)):
    assert_cabang_access(user, body.cabang_id)
    new_id = repo.create_entry(
        body.cabang_id, body.tanggal, body.jenis, body.nama_pengeluaran, body.nominal, user["id"],
    )
    log_activity(
        user["id"], user["username"], "CREATE", "pendapatan_pengeluaran_harian",
        new_id, f"{body.jenis}: {body.nama_pengeluaran}", body.cabang_id,
    )
    return {"id": new_id}


@router.put("/{entry_id}")
def update_entry(entry_id: int, body: PendapatanPengeluaranUpdate, user: dict = Depends(get_current_user)):
    cabang_id = _assert_entry_access(user, entry_id)
    repo.update_entry(entry_id, body.tanggal, body.jenis, body.nama_pengeluaran, body.nominal)
    log_activity(
        user["id"], user["username"], "UPDATE", "pendapatan_pengeluaran_harian",
        entry_id, f"{body.jenis}: {body.nama_pengeluaran}", cabang_id,
    )
    return {"ok": True}


@router.delete("/{entry_id}")
def delete_entry(entry_id: int, user: dict = Depends(get_current_user)):
    cabang_id = _assert_entry_access(user, entry_id)
    repo.delete_entry(entry_id)
    log_activity(user["id"], user["username"], "DELETE", "pendapatan_pengeluaran_harian", entry_id, None, cabang_id)
    return {"ok": True}


@router.get("/summary/harian")
def summary_harian(cabang_id: int, tanggal: date, user: dict = Depends(get_current_user)):
    assert_cabang_access(user, cabang_id)
    return repo.get_daily_summary(cabang_id, tanggal)


@router.get("/summary/bulanan")
def summary_bulanan(cabang_id: int, bulan: int, tahun: int, user: dict = Depends(get_current_user)):
    assert_cabang_access(user, cabang_id)
    return repo.get_monthly_summary(cabang_id, bulan, tahun)