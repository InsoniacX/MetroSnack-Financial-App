"""Repository orchestration for live monthly carry-forward balances."""
from repositories import finance_repo
from services.finance_service import hitung_riwayat_hutang


def get_history(cabang_id=None, through_folder_id=None, active_only=False):
    return hitung_riwayat_hutang(finance_repo.get_monthly_totals(
        cabang_id, through_folder_id, active_only,
    ))


def get_folder_balance(folder_id, cabang_id):
    periods, _ = get_history(cabang_id, through_folder_id=folder_id)
    return next((p for p in periods if p["folder_id"] == folder_id), None)
