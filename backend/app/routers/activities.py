from typing import Any

from fastapi import APIRouter

from app.services.postgres import pg_service

router = APIRouter()


@router.get("/")
def list_activities(limit: int = 50) -> list[dict[str, Any]]:
    return pg_service.fetch_activities(limit=limit)


@router.get("/health")
def list_health_daily(limit: int = 30) -> list[dict[str, Any]]:
    return pg_service.fetch_health_daily(limit=limit)
