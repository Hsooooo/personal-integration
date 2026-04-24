import os
import time
import json
import logging
import datetime
import functools
from typing import Any

from garminconnect import Garmin
import psycopg2
from psycopg2.extras import Json
import redis
from cryptography.fernet import Fernet
import base64
import httpx

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
)
logger = logging.getLogger("worker-garmin")

POSTGRES_HOST = os.getenv("POSTGRES_HOST", "postgres")
POSTGRES_DB = os.getenv("POSTGRES_DB", "pi_db")
POSTGRES_USER = os.getenv("POSTGRES_USER", "pi_user")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "password")
BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8000")
WORKER_TOKEN = os.getenv("WORKER_TOKEN", "worker-secret-token")
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production-32-char-min")

MAX_RETRIES = 3
RETRY_DELAY_BASE = 5
TOKEN_DIR = "/root/.garminconnect"
STREAM_NAME = "garmin-sync"
CONSUMER_GROUP = "garmin-workers"


def retry_with_backoff(max_retries=MAX_RETRIES, base_delay=RETRY_DELAY_BASE):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    delay = base_delay * (2 ** attempt)
                    logger.warning(f"{func.__name__} failed (attempt {attempt + 1}/{max_retries}): {e}")
                    if attempt < max_retries - 1:
                        logger.info(f"Retrying in {delay} seconds...")
                        time.sleep(delay)
            logger.error(f"{func.__name__} failed after {max_retries} attempts")
            raise last_exception
        return wrapper
    return decorator


@retry_with_backoff()
def get_db_connection():
    return psycopg2.connect(
        host=POSTGRES_HOST,
        database=POSTGRES_DB,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
        connect_timeout=10,
    )


def get_fernet() -> Fernet:
    key = base64.urlsafe_b64encode(SECRET_KEY.ljust(32)[:32].encode())
    return Fernet(key)


def get_user_credentials(user_id: int):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT garmin_email, garmin_password_encrypted FROM users WHERE id = %s",
        (user_id,),
    )
    row = cur.fetchone()
    cur.close()
    conn.close()
    if row and row[0] and row[1]:
        fernet = get_fernet()
        try:
            decrypted_password = fernet.decrypt(row[1].encode()).decode()
            return row[0], decrypted_password
        except Exception as e:
            logger.error(f"Failed to decrypt password for user {user_id}: {e}")
            return None, None
    return None, None


def save_daily_stats(stats: dict[str, Any]):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO health_daily (
            date, sleep_hours, sleep_score, resting_hr, hrv_status,
            stress_level, body_battery_max, body_battery_min, raw_data, updated_at
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
        ON CONFLICT (date) DO UPDATE SET
            sleep_hours = EXCLUDED.sleep_hours,
            sleep_score = EXCLUDED.sleep_score,
            resting_hr = EXCLUDED.resting_hr,
            hrv_status = EXCLUDED.hrv_status,
            stress_level = EXCLUDED.stress_level,
            body_battery_max = EXCLUDED.body_battery_max,
            body_battery_min = EXCLUDED.body_battery_min,
            raw_data = EXCLUDED.raw_data,
            updated_at = NOW();
        """,
        (
            stats["date"],
            stats.get("sleep_hours"),
            stats.get("sleep_score"),
            stats.get("resting_hr"),
            stats.get("hrv_status"),
            stats.get("stress_level"),
            stats.get("body_battery_max"),
            stats.get("body_battery_min"),
            Json(stats),
        ),
    )
    conn.commit()
    cur.close()
    conn.close()
    logger.info(f"Saved daily stats for {stats['date']}")


def save_activity(activity: dict[str, Any]):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO exercise_activity (
            activity_id, activity_type, activity_name, start_time, duration_sec,
            distance_meters, avg_hr, max_hr, avg_pace, calories, elevation_gain, raw_data
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (activity_id) DO UPDATE SET
            activity_type = EXCLUDED.activity_type,
            activity_name = EXCLUDED.activity_name,
            duration_sec = EXCLUDED.duration_sec,
            distance_meters = EXCLUDED.distance_meters,
            avg_hr = EXCLUDED.avg_hr,
            max_hr = EXCLUDED.max_hr,
            avg_pace = EXCLUDED.avg_pace,
            calories = EXCLUDED.calories,
            elevation_gain = EXCLUDED.elevation_gain,
            raw_data = EXCLUDED.raw_data;
        """,
        (
            activity["activity_id"],
            activity.get("activity_type"),
            activity.get("activity_name"),
            activity.get("start_time"),
            activity.get("duration_sec"),
            activity.get("distance_meters"),
            activity.get("avg_hr"),
            activity.get("max_hr"),
            activity.get("avg_pace"),
            activity.get("calories"),
            activity.get("elevation_gain"),
            Json(activity.get("raw_data", {})),
        ),
    )
    conn.commit()
    cur.close()
    conn.close()
    logger.info(f"Saved activity {activity['activity_id']}: {activity.get('activity_name')}")


def save_activity_laps(activity_id: int, laps: list[dict]):
    if not laps:
        return
    conn = get_db_connection()
    cur = conn.cursor()
    for idx, lap in enumerate(laps, start=1):
        avg_speed = lap.get("averageSpeed")
        avg_pace = None
        if avg_speed and avg_speed > 0:
            pace_sec_per_km = 1000 / float(avg_speed)
            minutes = int(pace_sec_per_km // 60)
            seconds = int(pace_sec_per_km % 60)
            avg_pace = f"{minutes}:{seconds:02d}"

        cur.execute(
            """
            INSERT INTO exercise_lap (
                activity_id, lap_index, start_time_gmt,
                distance_meters, duration_sec, avg_speed_mps, avg_pace,
                avg_hr, max_hr, raw_data
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (activity_id, lap_index) DO UPDATE SET
                start_time_gmt = EXCLUDED.start_time_gmt,
                distance_meters = EXCLUDED.distance_meters,
                duration_sec = EXCLUDED.duration_sec,
                avg_speed_mps = EXCLUDED.avg_speed_mps,
                avg_pace = EXCLUDED.avg_pace,
                avg_hr = EXCLUDED.avg_hr,
                max_hr = EXCLUDED.max_hr,
                raw_data = EXCLUDED.raw_data;
            """,
            (
                activity_id,
                idx,
                lap.get("startTimeGMT"),
                lap.get("distance"),
                lap.get("duration"),
                avg_speed,
                avg_pace,
                lap.get("averageHR"),
                lap.get("maxHR"),
                Json(lap),
            ),
        )
    conn.commit()
    cur.close()
    conn.close()
    logger.info(f"Saved {len(laps)} laps for activity {activity_id}")


def format_pace(speed_mps):
    if not speed_mps or speed_mps <= 0:
        return None
    pace_sec_per_km = 1000 / float(speed_mps)
    minutes = int(pace_sec_per_km // 60)
    seconds = int(pace_sec_per_km % 60)
    return f"{minutes}:{seconds:02d}"


def login_garmin(email: str, password: str) -> Garmin:
    os.makedirs(TOKEN_DIR, exist_ok=True)
    client = Garmin(email, password)
    try:
        client.login(TOKEN_DIR)
        client.get_user_summary(datetime.date.today().isoformat())
        logger.info("Garmin session loaded and validated.")
        return client
    except Exception as e:
        logger.info(f"Session invalid or expired: {e}")
        logger.info("Attempting fresh Garmin login...")
        client.login()
        logger.info("New Garmin session saved.")
        return client


def sync_all_activities(client: Garmin, user_id: int):
    start = 0
    limit = 100
    total_synced = 0
    while True:
        try:
            activities = client.get_activities(start, limit)
            if not activities:
                logger.info(f"No more activities at start={start}. Total synced: {total_synced}")
                break
            for act in activities:
                try:
                    activity_id = act.get("activityId")
                    if not activity_id:
                        continue
                    activity_data = {
                        "activity_id": activity_id,
                        "activity_type": act.get("activityType", {}).get("typeKey", "unknown"),
                        "activity_name": act.get("activityName", ""),
                        "start_time": act.get("startTimeLocal"),
                        "duration_sec": int(act.get("duration", 0)),
                        "distance_meters": act.get("distance"),
                        "avg_hr": act.get("averageHR"),
                        "max_hr": act.get("maxHR"),
                        "avg_pace": format_pace(act.get("averageSpeed")),
                        "calories": act.get("calories"),
                        "elevation_gain": act.get("elevationGain"),
                        "raw_data": act,
                    }
                    save_activity(activity_data)
                    try:
                        splits = client.get_activity_splits(activity_id)
                        laps = splits.get("lapDTOs", []) if isinstance(splits, dict) else []
                        save_activity_laps(activity_id, laps)
                    except Exception as e:
                        logger.warning(f"Failed to fetch/save laps for activity {activity_id}: {e}")
                except Exception as e:
                    logger.error(f"Failed to process activity {act.get('activityId')}: {e}")
                    continue
            total_synced += len(activities)
            logger.info(f"Synced batch: {len(activities)} activities (total: {total_synced})")
            start += limit
        except Exception as e:
            logger.error(f"Failed to fetch activities batch at start={start}: {e}")
            break
    return total_synced


def sync_health_for_user(client: Garmin, user_id: int, days: int = 30):
    today = datetime.date.today()
    total_saved = 0
    for i in range(days):
        sync_date = today - datetime.timedelta(days=i)
        sync_date_str = sync_date.isoformat()
        try:
            summary = client.get_user_summary(sync_date_str)
            sleep_data = client.get_sleep_data(sync_date_str)
            try:
                hrv_data = client.get_hrv_data(sync_date_str)
                hrv_status = hrv_data.get("hrvSummary", {}).get("status", "N/A")
            except Exception:
                hrv_status = "N/A"

            sleep_dto = sleep_data.get("dailySleepDto") or sleep_data.get("dailySleepDTO") or {}
            sleep_seconds = sleep_dto.get("sleepTimeSeconds", 0) or 0
            sleep_hours = round(sleep_seconds / 3600, 1)
            sleep_score = (
                sleep_dto.get("sleepScoreValue")
                or (sleep_dto.get("sleepScores") or {}).get("overall", {}).get("value")
                or 0
            )

            stats = {
                "date": sync_date_str,
                "sleep_hours": sleep_hours,
                "sleep_score": int(sleep_score) if sleep_score is not None else 0,
                "resting_hr": summary.get("restingHeartRate", 0),
                "hrv_status": hrv_status,
                "stress_level": summary.get("averageStressLevel", 0),
                "body_battery_max": summary.get("bodyBatteryMostRecentValue", 0),
                "body_battery_min": 0,
            }

            if "bodyBatteryValuesArray" in summary:
                bb_values = [item[1] for item in summary["bodyBatteryValuesArray"] if item[1] is not None]
                if bb_values:
                    stats["body_battery_max"] = max(bb_values)
                    stats["body_battery_min"] = min(bb_values)

            save_daily_stats(stats)
            total_saved += 1
        except Exception as e:
            logger.error(f"Failed to fetch health for {sync_date_str}: {e}")
    logger.info(f"Synced {total_saved} daily health records for user {user_id}")
    return total_saved


def notify_graph_sync(since: str | None = None):
    try:
        resp = httpx.post(
            f"{BACKEND_URL}/api/v1/graph/sync",
            headers={"X-Worker-Token": WORKER_TOKEN},
            params={"since": since} if since else None,
            timeout=120.0,
        )
        resp.raise_for_status()
        logger.info(f"Triggered backend graph sync: {resp.json()}")
    except Exception as e:
        logger.warning(f"Failed to trigger backend graph sync: {e}")


def process_sync_job(user_id: int, sync_type: str):
    logger.info(f"Processing sync job for user {user_id}, type={sync_type}")

    email, password = get_user_credentials(user_id)
    if not email or not password:
        raise ValueError(f"Garmin credentials not found or invalid for user {user_id}")

    client = login_garmin(email, password)

    activity_count = sync_all_activities(client, user_id)
    health_count = sync_health_for_user(client, user_id, days=30)

    notify_graph_sync()

    logger.info(
        f"Sync job completed for user {user_id}: "
        f"{activity_count} activities, {health_count} health records"
    )
    return {"activities": activity_count, "health": health_count}


def main():
    redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

    try:
        redis_client.xgroup_create(STREAM_NAME, CONSUMER_GROUP, id="0", mkstream=True)
        logger.info(f"Created consumer group {CONSUMER_GROUP}")
    except redis.ResponseError as e:
        if "BUSYGROUP" in str(e):
            logger.info(f"Consumer group {CONSUMER_GROUP} already exists")
        else:
            raise

    logger.info("Worker started. Waiting for sync jobs from Redis Stream...")

    while True:
        try:
            messages = redis_client.xreadgroup(
                CONSUMER_GROUP,
                "worker-1",
                {STREAM_NAME: ">"},
                block=5000,
                count=1,
            )

            if not messages:
                continue

            for stream_name, entries in messages:
                for entry_id, fields in entries:
                    user_id = int(fields.get("user_id"))
                    sync_type = fields.get("sync_type", "full")

                    try:
                        process_sync_job(user_id, sync_type)
                        redis_client.xack(STREAM_NAME, CONSUMER_GROUP, entry_id)
                        logger.info(f"Job {entry_id} completed and acknowledged for user {user_id}")
                    except Exception as e:
                        logger.error(f"Job {entry_id} failed for user {user_id}: {e}")
                        # Do not ACK - the message will remain pending for retry

        except Exception as e:
            logger.error(f"Consumer loop error: {e}")
            time.sleep(5)


if __name__ == "__main__":
    main()
