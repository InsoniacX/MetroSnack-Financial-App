from fastapi import APIRouter, Depends, HTTPException
from auth.dependencies import get_current_user, require_admin, assert_cabang_access
from models.schemas import UserCreate, UserUpdate, ResetPasswordRequest
from repositories import user_repo
from repositories.activity_repo import log_activity

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/username-exists")
def check_username_exists(username: str, user: dict = Depends(get_current_user)):
    return {"exists": user_repo.username_exists(username)}


@router.get("")
def list_users(cabang_id: int | None = None, user: dict = Depends(get_current_user)):
    if cabang_id is not None:
        assert_cabang_access(user, cabang_id)
    elif user["role"] != "admin":
        cabang_id = user["cabang_id"]
    return user_repo.get_all_users(cabang_id)


@router.post("")
def create_user(body: UserCreate, user: dict = Depends(require_admin)):
    if user_repo.username_exists(body.username):
        raise HTTPException(status_code=409, detail="Username sudah dipakai")
    new_id = user_repo.create_user(body.username, body.password, body.nama_lengkap, body.role, body.cabang_id)
    log_activity(user["id"], user["username"], "CREATE", "user", new_id, body.username, body.cabang_id)
    return {"id": new_id}


@router.put("/{user_id}")
def update_user(user_id: int, body: UserUpdate, user: dict = Depends(require_admin)):
    user_repo.update_user(user_id, body.nama_lengkap, body.role)
    log_activity(user["id"], user["username"], "UPDATE", "user", user_id, body.nama_lengkap, None)
    return {"ok": True}


@router.patch("/{user_id}/aktif")
def set_user_aktif(user_id: int, aktif: bool, user: dict = Depends(require_admin)):
    user_repo.set_aktif(user_id, aktif)
    log_activity(user["id"], user["username"], "UPDATE", "user", user_id, f"aktif={aktif}", None)
    return {"ok": True}


@router.post("/{user_id}/reset-password")
def reset_password(user_id: int, body: ResetPasswordRequest, user: dict = Depends(require_admin)):
    user_repo.reset_password(user_id, body.new_password)
    log_activity(user["id"], user["username"], "UPDATE", "user", user_id, "Reset password", None)
    return {"ok": True}


@router.delete("/{user_id}")
def delete_user(user_id: int, user: dict = Depends(require_admin)):
    user_repo.delete_user(user_id)
    log_activity(user["id"], user["username"], "DELETE", "user", user_id, None, None)
    return {"ok": True}
