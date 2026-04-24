from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel


class HealthDaily(BaseModel):
    date: date
    sleep_hours: Optional[float] = None
    sleep_score: Optional[int] = None
    resting_hr: Optional[int] = None
    hrv_status: Optional[str] = None
    stress_level: Optional[int] = None
    body_battery_max: Optional[int] = None
    body_battery_min: Optional[int] = None


class ExerciseActivity(BaseModel):
    activity_id: int
    activity_type: Optional[str] = None
    activity_name: Optional[str] = None
    start_time: Optional[datetime] = None
    duration_sec: Optional[int] = None
    distance_meters: Optional[float] = None
    avg_hr: Optional[int] = None
    max_hr: Optional[int] = None
    avg_pace: Optional[str] = None
    calories: Optional[int] = None
    elevation_gain: Optional[float] = None


class SyncResult(BaseModel):
    synced_activities: int
    synced_health: int


class GraphData(BaseModel):
    nodes: list[dict]
    edges: list[dict]
