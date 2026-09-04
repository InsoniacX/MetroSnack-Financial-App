from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query

from auth.dependencies import assert_cabang_access, get_current_user
from models.schemas import (
    PendapatanPengeluaranCreate,
    PendapatanPengeluaranUpdate,
)
from repositories import cabang_repo
from repositories import pendapatan_pengeluaran_repo as repo
from repositories.activity_repo import log_activity

router = APIRouter(prefix="/pendapatan-pengeluaran", tags=["pendapatan-pengeluaran"])


def _assert_feature_access(user: dict, cabang_id: int):
    assert_cabang_access(user, cabang_id)

    nama_cabang = cabang_repo.get_cabang_name(cabang_id)

    if nama_cabang is None:
        raise HTTPException(
            status_code=404,
            detail="Cabang tidak ditemukan",
        )


def _assert_entry_access(user, entry_id):
    header = repo.get_entry_header(entry_id)

    if header is None:
        raise HTTPException(status_code=404, detail="Data tidak ditemukan")

    _, cabang_id = header
    _assert_feature_access(user, cabang_id)
    return cabang_id


@router.get("")
def list_entries(
    cabang_id: int = Query(..., gt=0),
    tanggal_awal: date | None = None,
    tanggal_akhir: date | None = None,
    jenis: Literal["pendapatan", "pengeluaran"] | None = None,
    limit: int = Query(default=200, ge=1, le=500),
    user: dict = Depends(get_current_user),
):
    if tanggal_awal and tanggal_akhir and tanggal_awal > tanggal_akhir:
        raise HTTPException(
            status_code=422,
            detail="tanggal_awal tidak boleh melewati tanggal_akhir",
        )

    _assert_feature_access(user, cabang_id)
    return repo.get_entries(
        cabang_id,
        tanggal_awal,
        tanggal_akhir,
        jenis,
        limit,
    )


@router.post("")
def create_entry(body: PendapatanPengeluaranCreate, user: dict = Depends(get_current_user)):
    _assert_feature_access(user, body.cabang_id)
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
def summary_harian(
    cabang_id: int = Query(..., gt=0),
    tanggal: date = Query(...),
    user: dict = Depends(get_current_user),
):
    _assert_feature_access(user, cabang_id)
    return repo.get_daily_summary(cabang_id, tanggal)


@router.get("/summary/bulanan")
def summary_bulanan(
    cabang_id: int = Query(..., gt=0),
    bulan: int = Query(..., ge=1, le=12),
    tahun: int = Query(..., ge=2000, le=2100),
    user: dict = Depends(get_current_user),
):
    _assert_feature_access(user, cabang_id)
    return repo.get_monthly_summary(cabang_id, bulan, tahun)