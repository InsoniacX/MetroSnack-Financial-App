from fastapi import HTTPException, status

from auth.dependencies import (
    assert_cabang_access,
    is_pusat_admin,
)
from repositories import cabang_repo


_ZEBOR_CABANG_NAME = "Zebor"


def assert_zebor_feature_access(
    user: dict,
    cabang_id: int,
):
    """
    Admin pusat dapat mengakses fitur untuk semua cabang.

    Admin cabang dan karyawan hanya dapat menggunakan fitur ini
    apabila cabangnya adalah Zebor.
    """
    assert_cabang_access(user, cabang_id)

    nama_cabang = cabang_repo.get_cabang_name(cabang_id)

    if nama_cabang is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cabang tidak ditemukan",
        )

    if is_pusat_admin(user):
        return

    if nama_cabang.strip().casefold() != _ZEBOR_CABANG_NAME.casefold():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Fitur ini hanya tersedia untuk cabang Zebor",
        )