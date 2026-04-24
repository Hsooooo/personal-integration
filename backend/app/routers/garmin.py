from fastapi import APIRouter, Depends, HTTPException

from app.auth import get_current_active_user
from app.models.user import User
from app.services.redis_stream import redis_producer

router = APIRouter()


@router.post("/sync")
async def trigger_garmin_sync(
    sync_type: str = "full",
    current_user: User = Depends(get_current_active_user),
):
    if not current_user.garmin_email:
        raise HTTPException(
            status_code=400,
            detail="Garmin credentials not configured. Please set them in Settings.",
        )

    msg_id = redis_producer.publish_sync_job(current_user.id, sync_type)
    return {
        "status": "queued",
        "message_id": msg_id,
        "sync_type": sync_type,
        "user_id": current_user.id,
    }


@router.get("/status")
async def garmin_status(
    current_user: User = Depends(get_current_active_user),
):
    pending = redis_producer.get_pending_count()
    return {
        "status": "active",
        "pending_jobs": pending,
        "user_garmin_configured": bool(current_user.garmin_email),
    }
