from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# ------------------- Auth -------------------

class UserRegister(BaseModel):
    username: str
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ------------------- User -------------------

class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: str
    garmin_email: Optional[str] = None
    is_admin: bool
    created_at: datetime


class UserUpdate(BaseModel):
    garmin_email: Optional[str] = None
    garmin_password: Optional[str] = None


# ------------------- Activity -------------------

class ExerciseActivityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    activity_id: int
    activity_type: Optional[str] = None
    activity_name: Optional[str] = None
    start_time: Optional[datetime] = None
    distance_meters: Optional[Decimal] = None
    duration_sec: Optional[Decimal] = None
    avg_hr: Optional[int] = None
    max_hr: Optional[int] = None
    avg_pace: Optional[str] = None
    calories: Optional[int] = None
    elevation_gain: Optional[Decimal] = None
    is_race: bool = False
    race_type: Optional[str] = None
    race_prep_weeks: Optional[int] = 12


class ExerciseLapOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    activity_id: int
    lap_index: int
    distance_meters: Optional[Decimal] = None
    duration_sec: Optional[Decimal] = None
    avg_pace: Optional[str] = None
    avg_hr: Optional[int] = None
    max_hr: Optional[int] = None


class ActivityDetailOut(ExerciseActivityOut):
    laps: list[ExerciseLapOut] = []


class ActivityUpdate(BaseModel):
    is_race: Optional[bool] = None
    race_type: Optional[str] = Field(None, pattern=r"^(10k|half|full)$")
    race_prep_weeks: Optional[int] = Field(None, ge=4, le=16)


class PaginatedActivities(BaseModel):
    items: list[ExerciseActivityOut]
    total: int
    limit: int
    offset: int


class WeeklyStat(BaseModel):
    week: str
    total_km: float
    runs: int
    avg_hr: float


# ------------------- Health -------------------

class HealthDailyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    date: date
    sleep_hours: Optional[Decimal] = None
    sleep_score: Optional[int] = None
    resting_hr: Optional[int] = None
    hrv_status: Optional[str] = None
    stress_level: Optional[int] = None
    body_battery_max: Optional[int] = None
    body_battery_min: Optional[int] = None


# ------------------- Graph -------------------

class GraphSyncResult(BaseModel):
    status: str = "success"
    nodes_created: int
    nodes_updated: int
    edges_created: int
    activities_processed: int


class CypherQuery(BaseModel):
    cypher: str


class GraphSchema(BaseModel):
    node_labels: list[str]
    edge_types: list[str]


class RaceComparison(BaseModel):
    race_ids: list[str]


class RaceSyncRequest(BaseModel):
    activity_id: int
    race_type: str
    prep_weeks: int = 12
