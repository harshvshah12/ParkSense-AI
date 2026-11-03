"""
Results router — exposes job history endpoints.
"""
from fastapi import APIRouter

router = APIRouter()


@router.get("/", summary="List recent jobs (in-memory)")
async def list_results():
    """Returns a list of recent job IDs (stub — use a DB in production)."""
    return {"message": "Implement with a database for persistent history."}
