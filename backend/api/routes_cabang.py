from fastapi import APIRouter, Depends, HTTPException
from auth.dependencies import get_current_user, require_admin
from models.schemas import CabangCreate, CabangUpdate
from repositories import cabang_repo
from repositories.activity_repo import log_activity

router = APIRouter(prefix="/cabang", tags=["cabang"])


@router.get("/name-exists")
def check_cabang_name_exists(nama: str, exclude_id: int | None = None, user: dict = Depends(get_current_user)):
    return {"exists": cabang_repo.cabang_name_exist(nama, exclude_id)}


@router.get("")
def list_cabang(active_only: bool = False, user: dict = Depends(get_current_user)):
    rows = cabang_repo.get_active_cabang() if active_only else cabang_repo.get_all_cabang()
    return rows


@router.post("")
def create_cabang(body: CabangCreate, user: dict = Depends(require_admin)):
    if cabang_repo.cabang_name_exist(body.nama_cabang):
        raise HTTPException(status_code=409, detail="Nama cabang sudah dipakai")
    new_id = cabang_repo.create_cabang(body.nama_cabang, body.alamat)
    log_activity(user["id"], user["username"], "CREATE", "cabang", new_id, body.nama_cabang, None)
    return {"id": new_id}


@router.put("/{cabang_id}")
def update_cabang(cabang_id: int, body: CabangUpdate, user: dict = Depends(require_admin)):
    if cabang_repo.cabang_name_exist(body.nama_cabang, exclude_id=cabang_id):
        raise HTTPException(status_code=409, detail="Nama cabang sudah dipakai")
    cabang_repo.update_cabang(cabang_id, body.nama_cabang, body.alamat)
    log_activity(user["id"], user["username"], "UPDATE", "cabang", cabang_id, body.nama_cabang, None)
    return {"ok": True}


@router.patch("/{cabang_id}/aktif")
def set_cabang_aktif(cabang_id: int, aktif: bool, user: dict = Depends(require_admin)):
    cabang_repo.set_cabang_aktif(cabang_id, aktif)
    log_activity(user["id"], user["username"], "UPDATE", "cabang", cabang_id, f"aktif={aktif}", None)
    return {"ok": True}
