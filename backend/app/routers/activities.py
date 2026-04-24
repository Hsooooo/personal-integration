from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_active_user
from app.database import get_db
from app.models.schemas import (
    PaginatedActivities,
    ExerciseActivityOut,
    ActivityDetailOut,
    ExerciseLapOut,
    WeeklyStat,
)
from app.models.garmin import ExerciseActivity, ExerciseLap
from app.models.user import User

router = APIRouter()


@router.get("/", response_model=PaginatedActivities)
async def list_activities(
    limit: int = 20,
    offset: int = 0,
    order_by: str = "start_time",
    order: str = "desc",
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    order_col = getattr(ExerciseActivity, order_by, ExerciseActivity.start_time)
    if order == "desc":
        order_col = desc(order_col)

    total_result = await db.execute(select(func.count()).select_from(ExerciseActivity))
    total = total_result.scalar_one()

    result = await db.execute(
        select(ExerciseActivity)
        .order_by(order_col)
        .limit(limit)
        .offset(offset)
    )
    items = result.scalars().all()

    return {
        "items": [ExerciseActivityOut.model_validate(i) for i in items],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/{activity_id}", response_model=ActivityDetailOut)
async def get_activity(
    activity_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    result = await db.execute(
        select(ExerciseActivity).where(ExerciseActivity.activity_id == activity_id)
    )
    activity = result.scalar_one_or_none()
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    laps_result = await db.execute(
        select(ExerciseLap).where(ExerciseLap.activity_id == activity_id)
    )
    laps = laps_result.scalars().all()

    return {
        **ExerciseActivityOut.model_validate(activity).model_dump(),
        "laps": [ExerciseLapOut.model_validate(l) for l in laps],
    }


@router.post("/sync")
async def trigger_sync(
    current_user: User = Depends(get_current_active_user),
):
    """Trigger graph sync from Postgres to Neo4j.
    
    Garmin data fetch is handled automatically by the worker every 30 minutes.
    This endpoint only triggers the graph sync portion.
    """
    from app.services.neo4j import neo4j_service
    from app.services.postgres import pg_service
    try:
        # Get latest activities and health from Postgres
        activities = pg_service.fetch_activities(limit=100)
        health = pg_service.fetch_health_daily(limit=30)
        neo4j_service.sync_activities(activities)
        neo4j_service.sync_health_daily(health)
        return {
            "status": "sync_triggered",
            "activities_synced": len(activities),
            "health_synced": len(health),
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Sync failed: {e}")


@router.get("/stats/weekly", response_model=list[WeeklyStat])
async def weekly_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    # Aggregate by ISO week
    from sqlalchemy import text
    query = text("""
        SELECT
            TO_CHAR(start_time, 'IYYY-IW') AS week,
            ROUND(SUM(distance_meters / 1000)::numeric, 2) AS total_km,
            COUNT(*) AS runs,
            ROUND(AVG(avg_hr)::numeric, 1) AS avg_hr
        FROM exercise_activity
        WHERE activity_type = 'running'
          AND start_time IS NOT NULL
        GROUP BY week
        ORDER BY week DESC
        LIMIT 52
    """)
    result = await db.execute(query)
    rows = result.mappings().all()
    return [
        WeeklyStat(
            week=r["week"],
            total_km=float(r["total_km"] or 0),
            runs=r["runs"],
            avg_hr=float(r["avg_hr"] or 0),
        )
        for r in rows
    ]
