from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Path, Query

from auth.dependencies import get_current_user
from auth.feature_access import assert_zebor_feature_access
from models.schemas import (
    PengambilanKasCreate,
    PengambilanKasUpdate,
)
from repositories import pengambilan_kas_repo as repo
from repositories.activity_repo import log_activity


SumberPengambilan = Literal["pabrik", "balaraja"]

router = APIRouter(
    prefix="/pengambilan-kas",
    tags=["pengambilan-kas"],
)


def _assert_date_range(tanggal_awal, tanggal_akhir):
    if (
        tanggal_awal is not None
        and tanggal_akhir is not None
        and tanggal_awal > tanggal_akhir
    ):
        raise HTTPException(
            status_code=422,
            detail="tanggal_awal tidak boleh melewati tanggal_akhir",
        )


def _assert_cabang_request(user, cabang_id):
    assert_zebor_feature_access(user, cabang_id)


def _get_authorized_header(user, sumber, entry_id):
    header = repo.get_pengambilan_kas_header(
        sumber,
        entry_id,
    )

    if header is None:
        raise HTTPException(
            status_code=404,
            detail="Data pengambilan kas tidak ditemukan",
        )

    _, cabang_id = header
    assert_zebor_feature_access(user, cabang_id)

    return header


@router.get("/{sumber}/summary")
def get_pengambilan_kas_summary(
    sumber: SumberPengambilan,
    cabang_id: int = Query(..., gt=0),
    tanggal_awal: date | None = None,
    tanggal_akhir: date | None = None,
    user: dict = Depends(get_current_user),
):
    _assert_date_range(tanggal_awal, tanggal_akhir)
    _assert_cabang_request(user, cabang_id)

    return repo.get_pengambilan_kas_summary(
        sumber,
        cabang_id,
        tanggal_awal,
        tanggal_akhir,
    )


@router.get("/{sumber}")
def list_pengambilan_kas(
    sumber: SumberPengambilan,
    cabang_id: int = Query(..., gt=0),
    tanggal_awal: date | None = None,
    tanggal_akhir: date | None = None,
    limit: int = Query(default=200, ge=1, le=500),
    user: dict = Depends(get_current_user),
):
    _assert_date_range(tanggal_awal, tanggal_akhir)
    _assert_cabang_request(user, cabang_id)

    return repo.get_pengambilan_kas(
        sumber,
        cabang_id,
        tanggal_awal,
        tanggal_akhir,
        limit,
    )


@router.post("/{sumber}")
def create_pengambilan_kas(
    sumber: SumberPengambilan,
    body: PengambilanKasCreate,
    user: dict = Depends(get_current_user),
):
    _assert_cabang_request(user, body.cabang_id)

    new_id = repo.create_pengambilan_kas(
        sumber,
        body.cabang_id,
        body.tanggal,
        body.keterangan,
        body.nominal,
        user["id"],
    )

    log_activity(
        user["id"],
        user["username"],
        "CREATE",
        f"pengambilan_{sumber}",
        new_id,
        f"{body.tanggal}: {body.keterangan}",
        body.cabang_id,
    )

    return {"id": new_id}


@router.put("/{sumber}/{entry_id}")
def update_pengambilan_kas(
    sumber: SumberPengambilan,
    body: PengambilanKasUpdate,
    entry_id: int = Path(..., gt=0),
    user: dict = Depends(get_current_user),
):
    header = _get_authorized_header(
        user,
        sumber,
        entry_id,
    )
    _, cabang_id = header

    repo.update_pengambilan_kas(
        sumber,
        entry_id,
        body.tanggal,
        body.keterangan,
        body.nominal,
    )

    log_activity(
        user["id"],
        user["username"],
        "UPDATE",
        f"pengambilan_{sumber}",
        entry_id,
        f"{body.tanggal}: {body.keterangan}",
        cabang_id,
    )

    return {"ok": True}


@router.delete("/{sumber}/{entry_id}")
def delete_pengambilan_kas(
    sumber: SumberPengambilan,
    entry_id: int = Path(..., gt=0),
    user: dict = Depends(get_current_user),
):
    header = _get_authorized_header(
        user,
        sumber,
        entry_id,
    )
    _, cabang_id = header

    repo.delete_pengambilan_kas(
        sumber,
        entry_id,
    )

    log_activity(
        user["id"],
        user["username"],
        "DELETE",
        f"pengambilan_{sumber}",
        entry_id,
        None,
        cabang_id,
    )

    return {"ok": True}