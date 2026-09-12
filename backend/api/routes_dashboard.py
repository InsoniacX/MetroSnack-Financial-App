from fastapi import APIRouter, Depends, Query
from auth.dependencies import (
    get_current_user,
    assert_cabang_access,
    is_pusat_admin,
    require_pusat_admin,
)
from repositories import folder_repo
from services.finance_service import ringkasan_seluruh_cabang
from services import debt_service

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary")
def dashboard_summary(cabang_id: int | None = None, user: dict = Depends(get_current_user)):
    if cabang_id is not None:
        assert_cabang_access(user, cabang_id)
    elif not is_pusat_admin(user):
        cabang_id = user["cabang_id"]

    _, branches = debt_service.get_history(cabang_id)
    return ringkasan_seluruh_cabang(branches)


@router.get("/cabang-summary")
def cabang_summary(
    user: dict = Depends(require_pusat_admin),
):
    """Ringkasan sederhana per-cabang (total folder + laba_bersih), dipakai
    halaman 'Pilih Cabang' -- BUKAN Sisa Hutang, pakai /dashboard/cabang-breakdown untuk itu."""
    return folder_repo.get_cabang_summary()


@router.get("/cabang-breakdown")
def cabang_breakdown(
    user: dict = Depends(require_pusat_admin),
):
    _, branches = debt_service.get_history(active_only=True)
    return sorted(branches, key=lambda b: b["nama_cabang"])


@router.get("/monthly-trend")
def monthly_trend(
    cabang_id: int | None = None, 
    limit_months: int = Query(default=6, ge=1, le=24),
    user: dict = Depends(get_current_user)
):
    if cabang_id is not None:
        assert_cabang_access(user, cabang_id)
    elif not is_pusat_admin(user):
        cabang_id = user["cabang_id"]

    periods, _ = debt_service.get_history(cabang_id)
    # Apply display limit only AFTER replaying older balances.
    return sorted(periods, key=lambda p: (p["tahun"], p["bulan"], p["folder_id"]))[-limit_months:]
