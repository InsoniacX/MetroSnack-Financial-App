from fastapi import APIRouter, Depends, HTTPException, status
from psycopg2 import errors as pg_errors

from auth.dependencies import (
    require_admin,
    assert_cabang_access,
    is_pusat_admin,
)
from models.schemas import (
    UserCreate,
    UserUpdate,
    ResetPasswordRequest,
)
from repositories import user_repo, cabang_repo
from repositories.activity_repo import log_activity


router = APIRouter(prefix="/users", tags=["users"])


def _get_accessible_target(actor: dict, user_id: int):
    target = user_repo.get_user_header(user_id)

    if target is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User tidak ditemukan",
        )

    target_cabang_id = target[3]

    if not is_pusat_admin(actor):
        assert_cabang_access(actor, target_cabang_id)

        target_id, _, target_role, _, _ = target

        if target_role == "admin" and target_id != actor["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin cabang tidak boleh mengelola akun admin lain",
            )

    return target


@router.get("/username-exists")
def check_username_exists(
    username: str,
    user: dict = Depends(require_admin),
):
    return {"exists": user_repo.username_exists(username)}


@router.get("")
def list_users(
    cabang_id: int | None = None,
    user: dict = Depends(require_admin),
):
    if cabang_id is not None:
        assert_cabang_access(user, cabang_id)
    elif not is_pusat_admin(user):
        cabang_id = user["cabang_id"]

    return user_repo.get_all_users(cabang_id)


@router.post("")
def create_user(
    body: UserCreate,
    user: dict = Depends(require_admin),
):
    if not is_pusat_admin(user):
        if body.role != "karyawan":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin cabang hanya boleh membuat akun karyawan",
            )

        assert_cabang_access(user, body.cabang_id)

    if (
        body.cabang_id is not None
        and cabang_repo.get_cabang_name(body.cabang_id) is None
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cabang tidak ditemukan",
        )

    if user_repo.username_exists(body.username):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username sudah dipakai",
        )

    try:
        new_id = user_repo.create_user(
            body.username,
            body.password,
            body.nama_lengkap,
            body.role,
            body.cabang_id,
        )
    except pg_errors.UniqueViolation:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username sudah dipakai",
        ) from None

    log_activity(
        user["id"],
        user["username"],
        "CREATE",
        "user",
        new_id,
        body.username,
        body.cabang_id,
    )

    return {"id": new_id}


@router.put("/{user_id}")
def update_user(
    user_id: int,
    body: UserUpdate,
    user: dict = Depends(require_admin),
):
    target = _get_accessible_target(user, user_id)

    _, target_username, target_role, target_cabang_id, _ = target

    if not is_pusat_admin(user) and body.role != target_role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Hanya admin pusat yang boleh mengubah role user",
        )

    if user_id == user["id"] and body.role != target_role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Anda tidak boleh mengubah role akun sendiri",
        )

    user_repo.update_user(
        user_id,
        body.nama_lengkap,
        body.role,
    )

    log_activity(
        user["id"],
        user["username"],
        "UPDATE",
        "user",
        user_id,
        f"Mengubah user {target_username}",
        target_cabang_id,
    )

    return {"ok": True}


@router.patch("/{user_id}/aktif")
def set_user_aktif(
    user_id: int,
    aktif: bool,
    user: dict = Depends(require_admin),
):
    target = _get_accessible_target(user, user_id)

    _, target_username, _, target_cabang_id, _ = target

    if user_id == user["id"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Anda tidak boleh mengubah status akun sendiri",
        )

    user_repo.set_aktif(user_id, aktif)

    log_activity(
        user["id"],
        user["username"],
        "UPDATE",
        "user",
        user_id,
        f"Mengubah status {target_username}: aktif={aktif}",
        target_cabang_id,
    )

    return {"ok": True}


@router.post("/{user_id}/reset-password")
def reset_password(
    user_id: int,
    body: ResetPasswordRequest,
    user: dict = Depends(require_admin),
):
    target = _get_accessible_target(user, user_id)

    _, target_username, _, target_cabang_id, _ = target

    user_repo.reset_password(
        user_id,
        body.new_password,
    )

    log_activity(
        user["id"],
        user["username"],
        "UPDATE",
        "user",
        user_id,
        f"Reset password user {target_username}",
        target_cabang_id,
    )

    return {"ok": True}


@router.delete("/{user_id}")
def delete_user(
    user_id: int,
    user: dict = Depends(require_admin),
):
    target = _get_accessible_target(user, user_id)

    _, target_username, _, target_cabang_id, _ = target

    if user_id == user["id"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Anda tidak boleh menghapus akun sendiri",
        )

    try:
        user_repo.delete_user(user_id)
    except pg_errors.ForeignKeyViolation:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "User memiliki riwayat data dan tidak dapat dihapus. "
                "Nonaktifkan akun sebagai gantinya."
            ),
        ) from None

    log_activity(
        user["id"],
        user["username"],
        "DELETE",
        "user",
        user_id,
        f"Menghapus user {target_username}",
        target_cabang_id,
    )

    return {"ok": True}