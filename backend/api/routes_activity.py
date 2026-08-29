from fastapi import APIRouter, Depends, Query
from auth.dependencies import get_current_user
from repositories import activity_repo

router = APIRouter(prefix="/activity-log", tags=["activity"])


@router.get("")
def list_activity(
    limit: int = Query(default=200, ge=1, le=500),
    user: dict = Depends(get_current_user),
):
    cabang_id = None if user["role"] == "admin" else user["cabang_id"]
    return activity_repo.get_recent_activities(cabang_id, limit)
