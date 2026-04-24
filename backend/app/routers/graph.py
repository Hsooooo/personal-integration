from typing import Any

from fastapi import APIRouter

from app.services.postgres import pg_service
from app.services.neo4j import neo4j_service

router = APIRouter()


@router.post("/sync")
def sync_graph() -> dict[str, Any]:
    activities = pg_service.fetch_activities(limit=1000)
    health = pg_service.fetch_health_daily(limit=365)
    neo4j_service.sync_activities(activities)
    neo4j_service.sync_health_daily(health)
    return {
        "synced_activities": len(activities),
        "synced_health": len(health),
    }


@router.get("/data")
def get_graph_data(limit: int = 100) -> dict[str, Any]:
    return neo4j_service.get_graph_data(limit=limit)
