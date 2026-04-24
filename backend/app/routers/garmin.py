from fastapi import APIRouter

router = APIRouter()


@router.post("/sync")
def trigger_garmin_sync():
    # In PoC, the worker runs on its own schedule.
    # This endpoint can be extended to trigger immediate sync via a message queue.
    return {"message": "Garmin sync is handled by the worker. It runs every 30 minutes."}


@router.get("/status")
def garmin_status():
    return {"status": "Worker runs on schedule", "interval_min": 30}
