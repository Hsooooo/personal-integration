import os
import logging
from typing import Any

import psycopg2
from psycopg2.extras import RealDictCursor, Json

logger = logging.getLogger("postgres")

POSTGRES_HOST = os.getenv("POSTGRES_HOST", "postgres")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DB = os.getenv("POSTGRES_DB", "pi_db")
POSTGRES_USER = os.getenv("POSTGRES_USER", "pi_user")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "password")


class PostgresService:
    def __init__(self):
        self.conn = None
        self._connect()

    def _connect(self):
        try:
            self.conn = psycopg2.connect(
                host=POSTGRES_HOST,
                port=POSTGRES_PORT,
                database=POSTGRES_DB,
                user=POSTGRES_USER,
                password=POSTGRES_PASSWORD,
                connect_timeout=10,
            )
            logger.info("Postgres connected.")
        except Exception as e:
            logger.error(f"Postgres connection failed: {e}")
            self.conn = None

    def is_healthy(self) -> bool:
        if self.conn is None:
            return False
        try:
            with self.conn.cursor() as cur:
                cur.execute("SELECT 1")
                return True
        except Exception as e:
            logger.warning(f"Postgres health check failed: {e}")
            return False

    def init_tables(self):
        if self.conn is None:
            logger.warning("Postgres not connected, skipping init_tables")
            return
        with self.conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS health_daily (
                    date DATE PRIMARY KEY,
                    sleep_hours NUMERIC,
                    sleep_score INTEGER,
                    resting_hr INTEGER,
                    hrv_status TEXT,
                    stress_level INTEGER,
                    body_battery_max INTEGER,
                    body_battery_min INTEGER,
                    raw_data JSONB,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS exercise_activity (
                    activity_id BIGINT PRIMARY KEY,
                    activity_type TEXT,
                    activity_name TEXT,
                    start_time TIMESTAMP,
                    duration_sec INTEGER,
                    distance_meters NUMERIC,
                    avg_hr INTEGER,
                    max_hr INTEGER,
                    avg_pace TEXT,
                    calories INTEGER,
                    elevation_gain NUMERIC,
                    raw_data JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS exercise_lap (
                    activity_id BIGINT NOT NULL,
                    lap_index INTEGER NOT NULL,
                    start_time_gmt TIMESTAMP,
                    distance_meters NUMERIC,
                    duration_sec NUMERIC,
                    avg_speed_mps NUMERIC,
                    avg_pace TEXT,
                    avg_hr INTEGER,
                    max_hr INTEGER,
                    calories NUMERIC,
                    raw_data JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (activity_id, lap_index)
                );
                """
            )
            self.conn.commit()
        logger.info("Postgres tables initialized.")

    def fetch_activities(self, limit: int = 50) -> list[dict[str, Any]]:
        if self.conn is None:
            return []
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT activity_id, activity_type, activity_name, start_time,
                       duration_sec, distance_meters, avg_hr, max_hr, avg_pace, calories
                FROM exercise_activity
                ORDER BY start_time DESC
                LIMIT %s
                """,
                (limit,),
            )
            return [dict(row) for row in cur.fetchall()]

    def fetch_health_daily(self, limit: int = 30) -> list[dict[str, Any]]:
        if self.conn is None:
            return []
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT date, sleep_hours, sleep_score, resting_hr, hrv_status,
                       stress_level, body_battery_max, body_battery_min
                FROM health_daily
                ORDER BY date DESC
                LIMIT %s
                """,
                (limit,),
            )
            return [dict(row) for row in cur.fetchall()]

    def close(self):
        if self.conn:
            self.conn.close()
            logger.info("Postgres connection closed.")


# Global singleton instance
pg_service = PostgresService()
