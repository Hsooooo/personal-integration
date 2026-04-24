from datetime import datetime, date
from decimal import Decimal

from sqlalchemy import BigInteger, Integer, String, Numeric, DateTime, Date, JSON, ForeignKey, func, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ExerciseActivity(Base):
    __tablename__ = "exercise_activity"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    activity_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    activity_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    activity_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    start_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    distance_meters: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    duration_sec: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
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
    __table_args__ = (UniqueConstraint("activity_id", "lap_index", name="uq_lap"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    activity_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("exercise_activity.activity_id", ondelete="CASCADE"), nullable=False)
    lap_index: Mapped[int] = mapped_column(Integer, nullable=False)
    start_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    distance_meters: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    duration_sec: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    avg_pace: Mapped[str | None] = mapped_column(String(10), nullable=True)
    avg_hr: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_hr: Mapped[int | None] = mapped_column(Integer, nullable=True)
    raw_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    activity: Mapped["ExerciseActivity"] = relationship("ExerciseActivity", back_populates="laps")


class HealthDaily(Base):
    __tablename__ = "health_daily"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    date: Mapped[date] = mapped_column(Date, unique=True, nullable=False)
    sleep_hours: Mapped[Decimal | None] = mapped_column(Numeric(4, 2), nullable=True)
    sleep_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    resting_hr: Mapped[int | None] = mapped_column(Integer, nullable=True)
    hrv_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    stress_level: Mapped[int | None] = mapped_column(Integer, nullable=True)
    body_battery_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    body_battery_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    raw_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class RunningRecord(Base):
    __tablename__ = "running_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    week: Mapped[str | None] = mapped_column(String(10), nullable=True)
    total_km: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    runs: Mapped[int | None] = mapped_column(Integer, nullable=True)
    avg_hr: Mapped[Decimal | None] = mapped_column(Numeric(5, 1), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
