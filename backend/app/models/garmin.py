from datetime import datetime, date
from decimal import Decimal

from sqlalchemy import BigInteger, Integer, String, Numeric, DateTime, Date, JSON, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ExerciseActivity(Base):
    __tablename__ = "exercise_activity"

    activity_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    activity_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    activity_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    start_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    distance_meters: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    duration_sec: Mapped[int | None] = mapped_column(Integer, nullable=True)
    avg_hr: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_hr: Mapped[int | None] = mapped_column(Integer, nullable=True)
    avg_pace: Mapped[str | None] = mapped_column(String(10), nullable=True)
    elevation_gain: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    calories: Mapped[int | None] = mapped_column(Integer, nullable=True)
    raw_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    laps: Mapped[list["ExerciseLap"]] = relationship("ExerciseLap", back_populates="activity", cascade="all, delete-orphan")


class ExerciseLap(Base):
    __tablename__ = "exercise_lap"

    activity_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("exercise_activity.activity_id", ondelete="CASCADE"), primary_key=True)
    lap_index: Mapped[int] = mapped_column(Integer, primary_key=True)
    start_time_gmt: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    distance_meters: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    duration_sec: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    avg_speed_mps: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    avg_pace: Mapped[str | None] = mapped_column(String(10), nullable=True)
    avg_hr: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_hr: Mapped[int | None] = mapped_column(Integer, nullable=True)
    calories: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    raw_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    activity: Mapped["ExerciseActivity"] = relationship("ExerciseActivity", back_populates="laps")


class HealthDaily(Base):
    __tablename__ = "health_daily"

    date: Mapped[date] = mapped_column(Date, primary_key=True)
    sleep_hours: Mapped[Decimal | None] = mapped_column(Numeric(4, 2), nullable=True)
    sleep_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    resting_hr: Mapped[int | None] = mapped_column(Integer, nullable=True)
    hrv_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    stress_level: Mapped[int | None] = mapped_column(Integer, nullable=True)
    body_battery_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    body_battery_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    raw_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class RunningRecord(Base):
    __tablename__ = "running_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    week: Mapped[str | None] = mapped_column(String(10), nullable=True)
    total_km: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    runs: Mapped[int | None] = mapped_column(Integer, nullable=True)
    avg_hr: Mapped[Decimal | None] = mapped_column(Numeric(5, 1), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
