from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Path, Query

from auth.dependencies import (
    assert_cabang_access,
    get_current_user,
)
from models.schemas import (
    OperasionalMobilCreate,
    OperasionalMobilUpdate,
)
from repositories import cabang_repo
from repositories import operasional_mobil_repo as repo
from repositories import supir_kenek_repo
from repositories.activity_repo import log_activity


router = APIRouter(
    prefix="/operasional-mobil",
    tags=["operasional-mobil"],
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
    assert_cabang_access(user, cabang_id)

    if cabang_repo.get_cabang_name(cabang_id) is None:
        raise HTTPException(
            status_code=404,
            detail="Cabang tidak ditemukan",
        )


def _get_authorized_header(user, operasional_id):
    header = repo.get_operasional_mobil_header(operasional_id)

    if header is None:
        raise HTTPException(
            status_code=404,
            detail="Data operasional mobil tidak ditemukan",
        )

    _, cabang_id, _, _ = header
    assert_cabang_access(user, cabang_id)

    return header


def _assert_person_selection(
    cabang_id,
    person_id,
    label,
    allowed_inactive_id=None,
):
    if person_id is None:
        return None

    header = supir_kenek_repo.get_supir_kenek_header(person_id)

    if header is None:
        raise HTTPException(
            status_code=422,
            detail=f"{label} tidak ditemukan",
        )

    _, person_cabang_id, _, aktif = header

    if person_cabang_id != cabang_id:
        raise HTTPException(
            status_code=422,
            detail=f"{label} harus berasal dari cabang yang sama",
        )

    if not aktif and person_id != allowed_inactive_id:
        raise HTTPException(
            status_code=422,
            detail=f"{label} sudah tidak aktif",
        )

    return header


@router.get("")
def list_operasional_mobil(
    cabang_id: int = Query(..., gt=0),
    tanggal_awal: date | None = None,
    tanggal_akhir: date | None = None,
    limit: int = Query(default=200, ge=1, le=500),
    user: dict = Depends(get_current_user),
):
    _assert_date_range(tanggal_awal, tanggal_akhir)
    _assert_cabang_request(user, cabang_id)

    return repo.get_operasional_mobil(
        cabang_id,
        tanggal_awal,
        tanggal_akhir,
        limit,
    )


@router.get("/summary")
def get_operasional_summary(
    cabang_id: int = Query(..., gt=0),
    tanggal_awal: date | None = None,
    tanggal_akhir: date | None = None,
    user: dict = Depends(get_current_user),
):
    _assert_date_range(tanggal_awal, tanggal_akhir)
    _assert_cabang_request(user, cabang_id)

    return repo.get_operasional_summary(
        cabang_id,
        tanggal_awal,
        tanggal_akhir,
    )


@router.post("")
def create_operasional_mobil(
    body: OperasionalMobilCreate,
    user: dict = Depends(get_current_user),
):
    _assert_cabang_request(user, body.cabang_id)

    supir_header = _assert_person_selection(
        body.cabang_id,
        body.supir_id,
        "Supir",
    )
    kenek_header = _assert_person_selection(
        body.cabang_id,
        body.kenek_id,
        "Kenek",
    )

    new_id = repo.create_operasional_mobil(
        body.cabang_id,
        body.tanggal,
        body.supir_id,
        body.kenek_id,
        body.uang_jalan,
        body.keterangan,
        user["id"],
    )

    nama_supir = supir_header[2]
    nama_kenek = (
        kenek_header[2]
        if kenek_header is not None
        else None
    )
    description = f"{body.tanggal}: {nama_supir}"

    if nama_kenek is not None:
        description += f" / {nama_kenek}"

    log_activity(
        user["id"],
        user["username"],
        "CREATE",
        "operasional_mobil",
        new_id,
        description,
        body.cabang_id,
    )

    return {"id": new_id}


@router.put("/{operasional_id}")
def update_operasional_mobil(
    body: OperasionalMobilUpdate,
    operasional_id: int = Path(..., gt=0),
    user: dict = Depends(get_current_user),
):
    header = _get_authorized_header(user, operasional_id)
    _, cabang_id, existing_supir_id, existing_kenek_id = header

    supir_header = _assert_person_selection(
        cabang_id,
        body.supir_id,
        "Supir",
        allowed_inactive_id=existing_supir_id,
    )
    kenek_header = _assert_person_selection(
        cabang_id,
        body.kenek_id,
        "Kenek",
        allowed_inactive_id=existing_kenek_id,
    )

    repo.update_operasional_mobil(
        operasional_id,
        body.tanggal,
        body.supir_id,
        body.kenek_id,
        body.uang_jalan,
        body.keterangan,
    )

    nama_supir = supir_header[2]
    nama_kenek = (
        kenek_header[2]
        if kenek_header is not None
        else None
    )
    description = f"{body.tanggal}: {nama_supir}"

    if nama_kenek is not None:
        description += f" / {nama_kenek}"

    log_activity(
        user["id"],
        user["username"],
        "UPDATE",
        "operasional_mobil",
        operasional_id,
        description,
        cabang_id,
    )

    return {"ok": True}


@router.delete("/{operasional_id}")
def delete_operasional_mobil(
    operasional_id: int = Path(..., gt=0),
    user: dict = Depends(get_current_user),
):
    header = _get_authorized_header(user, operasional_id)
    _, cabang_id, _, _ = header

    repo.delete_operasional_mobil(operasional_id)

    log_activity(
        user["id"],
        user["username"],
        "DELETE",
        "operasional_mobil",
        operasional_id,
        None,
        cabang_id,
    )

    return {"ok": True}