from fastapi import APIRouter, Depends, Query
from auth.dependencies import (
    get_current_user, 
    assert_cabang_access,
    require_admin,
)
from repositories import folder_repo
from services.finance_service import hitung_sisa_hutang

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary")
def dashboard_summary(cabang_id: int | None = None, user: dict = Depends(get_current_user)):
    if cabang_id is not None:
        assert_cabang_access(user, cabang_id)
    elif user["role"] != "admin":
        cabang_id = user["cabang_id"]

    raw = folder_repo.get_dashboard_summary_raw(cabang_id)
    return hitung_sisa_hutang(raw["modal_pusat"], raw["masuk_uang"], raw["masuk_barang"])


@router.get("/cabang-summary")
def cabang_summary(user: dict = Depends(require_admin)):
    """Ringkasan sederhana per-cabang (total folder + laba_bersih), dipakai
    halaman 'Pilih Cabang' -- BUKAN Sisa Hutang, pakai /dashboard/cabang-breakdown untuk itu."""
    return folder_repo.get_cabang_summary()


@router.get("/cabang-breakdown")
def cabang_breakdown(user: dict = Depends(require_admin)):
    rows = folder_repo.get_cabang_breakdown()
    result = []

    for cabang_id, nama_cabang, modal, omzet, barang in rows:
        breakdown = hitung_sisa_hutang(modal, omzet, barang)
        breakdown.update({
            "cabang_id": cabang_id, 
            "nama_cabang": nama_cabang
        })
        result.append(breakdown)
    return result


@router.get("/monthly-trend")
def monthly_trend(
    cabang_id: int | None = None, 
    limit_months: int = Query(default=6, ge=1, le=24),
    user: dict = Depends(get_current_user)
):
    if cabang_id is not None:
        assert_cabang_access(user, cabang_id)
    elif user["role"] != "admin":
        cabang_id = user["cabang_id"]

    rows = folder_repo.get_monthly_trend_raw(cabang_id, limit_months)
    result = []
    for folder_id, nama_folder, bulan, tahun, modal, omzet, barang in rows:
        breakdown = hitung_sisa_hutang(modal, omzet, barang)
        breakdown.update({"folder_id": folder_id, "nama_folder": nama_folder, "bulan": bulan, "tahun": tahun})
        result.append(breakdown)
    return result
