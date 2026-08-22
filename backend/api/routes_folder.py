from fastapi import APIRouter, Depends, HTTPException
from psycopg2 import errors as pg_errors
from auth.dependencies import get_current_user, assert_cabang_access
from models.schemas import FolderCreate
from repositories import folder_repo
from repositories.activity_repo import log_activity

router = APIRouter(prefix="/folders", tags=["folders"])


@router.get("")
def list_folders(cabang_id: int | None = None, user: dict = Depends(get_current_user)):
    if cabang_id is not None:
        assert_cabang_access(user, cabang_id)
    elif user["role"] != "admin":
        cabang_id = user["cabang_id"]
    return folder_repo.get_folders(cabang_id)


@router.post("")
def create_folder(body: FolderCreate, user: dict = Depends(get_current_user)):
    assert_cabang_access(user, body.cabang_id)
    try:
        new_id = folder_repo.create_folder(body.bulan, body.tahun, body.cabang_id, user["id"])
    except pg_errors.UniqueViolation:
        raise HTTPException(
            status_code=409,
            detail="Folder untuk bulan/tahun ini sudah ada untuk cabang tersebut",
        )
    log_activity(user["id"], user["username"], "CREATE", "folder_bulan", new_id, None, body.cabang_id)
    return {"id": new_id}


@router.get("/{folder_id}")
def get_folder(folder_id: int, user: dict = Depends(get_current_user)):
    header = folder_repo.get_folder_header(folder_id)
    if header is None:
        raise HTTPException(status_code=404, detail="Folder tidak ditemukan")
    _, _, cabang_id, _ = header
    assert_cabang_access(user, cabang_id)
    return header


@router.delete("/{folder_id}")
def delete_folder(folder_id: int, user: dict = Depends(get_current_user)):
    header = folder_repo.get_folder_header(folder_id)
    if header is None:
        raise HTTPException(status_code=404, detail="Folder tidak ditemukan")
    _, _, cabang_id, _ = header
    assert_cabang_access(user, cabang_id)
    folder_repo.delete_folder(folder_id)
    log_activity(user["id"], user["username"], "DELETE", "folder_bulan", folder_id, None, cabang_id)
    return {"ok": True}
