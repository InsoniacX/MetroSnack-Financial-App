from fastapi import APIRouter, Depends, HTTPException, Path, Query

from auth.dependencies import (
    assert_cabang_access,
    get_current_user,
    require_admin,
)
from models.schemas import SupirKenekCreate, SupirKenekUpdate
from repositories import cabang_repo
from repositories import supir_kenek_repo as repo
from repositories.activity_repo import log_activity


router = APIRouter(
    prefix="/supir-kenek",
    tags=["supir-kenek"],
)


def _assert_cabang_request(user, cabang_id):
    assert_cabang_access(user, cabang_id)

    if cabang_repo.get_cabang_name(cabang_id) is None:
        raise HTTPException(
            status_code=404,
            detail="Cabang tidak ditemukan",
        )


def _get_authorized_header(user, supir_kenek_id):
    header = repo.get_supir_kenek_header(supir_kenek_id)

    if header is None:
        raise HTTPException(
            status_code=404,
            detail="Supir/kenek tidak ditemukan",
        )

    _, cabang_id, _, _ = header
    assert_cabang_access(user, cabang_id)

    return header


@router.get("")
def list_supir_kenek(
    cabang_id: int = Query(..., gt=0),
    active_only: bool = True,
    user: dict = Depends(get_current_user),
):
    _assert_cabang_request(user, cabang_id)

    return repo.get_supir_kenek(
        cabang_id,
        active_only,
    )


@router.post("")
def create_supir_kenek(
    body: SupirKenekCreate,
    user: dict = Depends(require_admin),
):
    _assert_cabang_request(user, body.cabang_id)

    if repo.name_exists(body.cabang_id, body.nama):
        raise HTTPException(
            status_code=409,
            detail="Nama supir/kenek sudah terdaftar",
        )

    new_id = repo.create_supir_kenek(
        body.cabang_id,
        body.nama,
    )

    log_activity(
        user["id"],
        user["username"],
        "CREATE",
        "supir_kenek",
        new_id,
        body.nama,
        body.cabang_id,
    )

    return {"id": new_id}


@router.put("/{supir_kenek_id}")
def update_supir_kenek(
    body: SupirKenekUpdate,
    supir_kenek_id: int = Path(..., gt=0),
    user: dict = Depends(require_admin),
):
    header = _get_authorized_header(user, supir_kenek_id)
    _, cabang_id, _, _ = header

    if repo.name_exists(
        cabang_id,
        body.nama,
        exclude_id=supir_kenek_id,
    ):
        raise HTTPException(
            status_code=409,
            detail="Nama supir/kenek sudah terdaftar",
        )

    repo.update_supir_kenek(
        supir_kenek_id,
        body.nama,
    )

    log_activity(
        user["id"],
        user["username"],
        "UPDATE",
        "supir_kenek",
        supir_kenek_id,
        body.nama,
        cabang_id,
    )

    return {"ok": True}


@router.patch("/{supir_kenek_id}/aktif")
def set_supir_kenek_aktif(
    aktif: bool,
    supir_kenek_id: int = Path(..., gt=0),
    user: dict = Depends(require_admin),
):
    header = _get_authorized_header(user, supir_kenek_id)
    _, cabang_id, nama, _ = header

    repo.set_supir_kenek_aktif(
        supir_kenek_id,
        aktif,
    )

    log_activity(
        user["id"],
        user["username"],
        "UPDATE",
        "supir_kenek",
        supir_kenek_id,
        f"{nama}: aktif={aktif}",
        cabang_id,
    )

    return {"ok": True}