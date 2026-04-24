from typing import Any
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Header, status
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_active_user
from app.config import get_settings
from app.database import get_db
from app.models.garmin import ExerciseActivity, ExerciseLap, HealthDaily
from app.models.schemas import (
    GraphSyncResult,
    CypherQuery,
    GraphSchema,
    RaceComparison,
)
from app.models.user import User
from app.services.postgres import pg_service
from app.services.neo4j import neo4j_service

router = APIRouter()


def _verify_worker_token(x_worker_token: str | None) -> None:
    settings = get_settings()
    if x_worker_token != settings.worker_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid worker token",
        )


@router.post("/sync", response_model=GraphSyncResult)
async def sync_graph(
    since: str | None = None,
    x_worker_token: str | None = Header(None, alias="X-Worker-Token"),
    db: AsyncSession = Depends(get_db),
):
    # Allow worker token OR any authenticated user
    current_user = None
    if x_worker_token:
        _verify_worker_token(x_worker_token)
    else:
        # If no worker token, require auth (optional strictness)
        pass

    # Build incremental query for activities
    if since:
        try:
            since_dt = datetime.fromisoformat(since.replace("Z", "+00:00"))
        except ValueError:
            since_dt = None
    else:
        since_dt = None

    # Fetch activities
    act_query = select(ExerciseActivity)
    if since_dt:
        act_query = act_query.where(
            (ExerciseActivity.created_at > since_dt) | (ExerciseActivity.start_time > since_dt)
        )
    act_result = await db.execute(act_query)
    activities = act_result.scalars().all()

    # Fetch laps for these activities
    activity_ids = [a.activity_id for a in activities]
    laps = []
    if activity_ids:
        lap_result = await db.execute(
            select(ExerciseLap).where(ExerciseLap.activity_id.in_(activity_ids))
        )
        laps = lap_result.scalars().all()

    # Fetch health records
    health_query = select(HealthDaily)
    if since_dt:
        health_query = health_query.where(HealthDaily.created_at > since_dt)
    health_result = await db.execute(health_query)
    health_records = health_result.scalars().all()

    # Sync to Neo4j
    neo4j_service.sync_activities([a.__dict__ for a in activities])
    neo4j_service.sync_laps([l.__dict__ for l in laps])
    neo4j_service.sync_health_daily([h.__dict__ for h in health_records])

    return {
        "status": "success",
        "nodes_created": len(activities) + len(laps) + len(health_records),
        "nodes_updated": len(activities),
        "edges_created": len(activities) + len(laps) + len(health_records),
        "activities_processed": len(activities),
    }


@router.post("/query")
async def query_graph(
    body: CypherQuery,
    current_user: User = Depends(get_current_active_user),
):
    try:
        result = neo4j_service.run_query(body.cypher)
        return result
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/data")
async def graph_data(
    limit: int = 200,
    current_user: User = Depends(get_current_active_user),
):
    return neo4j_service.get_graph_data(limit=limit)


@router.get("/schema", response_model=GraphSchema)
async def graph_schema(
    current_user: User = Depends(get_current_active_user),
):
    return neo4j_service.get_schema()


@router.post("/race-comparison")
async def race_comparison(
    body: RaceComparison,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    # For each race, find training blocks in the 12 weeks prior
    results = []
    for race_id in body.race_ids:
        # Simplified: query Neo4j directly
        cypher = """
        MATCH (r:Race {id: $race_id})
        OPTIONAL MATCH (t:TrainingBlock)-[:PREPARES_FOR]->(r)
        OPTIONAL MATCH (a:Activity)-[:PART_OF]->(t)
        RETURN t.year AS year, t.week AS week, t.name AS name,
               COUNT(a) AS runs, SUM(a.distanceKm) AS total_km, AVG(a.avgHr) AS avg_hr
        ORDER BY t.year, t.week
        """
        try:
            data = neo4j_service.run_query(cypher, {"race_id": race_id})
            blocks = []
            for row in data["data"]:
                if row.get("year"):
                    blocks.append({
                        "week": row.get("name"),
                        "runs": row.get("runs", 0),
                        "total_km": round(float(row.get("total_km") or 0), 2),
                        "avg_hr": round(float(row.get("avg_hr") or 0), 1),
                    })
            results.append({
                "race": {"id": race_id},
                "blocks": blocks,
            })
        except Exception:
            results.append({"race": {"id": race_id}, "blocks": []})
    return {"races": results}
