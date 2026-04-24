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
import schedule
import httpx

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
)
logger = logging.getLogger("worker-garmin")

GARMIN_EMAIL = os.getenv("GARMIN_EMAIL")
GARMIN_PASSWORD = os.getenv("GARMIN_PASSWORD")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "postgres")
POSTGRES_DB = os.getenv("POSTGRES_DB", "pi_db")
POSTGRES_USER = os.getenv("POSTGRES_USER", "pi_user")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "password")
BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8000")

MAX_RETRIES = 3
RETRY_DELAY_BASE = 5
TOKEN_DIR = "/root/.garminconnect"


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


def format_pace(speed_mps):
    if not speed_mps or speed_mps <= 0:
        return None
    pace_sec_per_km = 1000 / float(speed_mps)
    minutes = int(pace_sec_per_km // 60)
    seconds = int(pace_sec_per_km % 60)
    return f"{minutes}:{seconds:02d}"


def login_garmin() -> Garmin:
    os.makedirs(TOKEN_DIR, exist_ok=True)
    client = Garmin(GARMIN_EMAIL, GARMIN_PASSWORD)
    # v0.3.0+: login() handles token save/load internally at ~/.garminconnect by default
    # We pass the token_dir explicitly to be safe.
    try:
        client.login(TOKEN_DIR)
        # Validate
        client.get_user_summary(datetime.date.today().isoformat())
        logger.info("Garmin session loaded and validated.")
        return client
    except Exception as e:
        logger.info(f"Session invalid or expired: {e}")
        logger.info("Attempting fresh Garmin login...")
        client.login()
        logger.info("New Garmin session saved.")
        return client


def sync_activities(client: Garmin):
    logger.info("Syncing exercise activities...")
    try:
        activities = client.get_activities(0, 10)
        if not activities:
            logger.info("No activities found.")
            return
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
            except Exception as e:
                logger.error(f"Failed to process activity {act.get('activityId')}: {e}")
                continue
        logger.info(f"Synced {len(activities)} activities.")
    except Exception as e:
        logger.error(f"Failed to sync activities: {e}")


def trigger_backend_sync():
    try:
        resp = httpx.post(f"{BACKEND_URL}/api/graph/sync", timeout=30.0)
        resp.raise_for_status()
        logger.info(f"Triggered backend graph sync: {resp.json()}")
    except Exception as e:
        logger.warning(f"Failed to trigger backend graph sync: {e}")


def run_sync():
    logger.info("Starting Garmin Sync...")
    sync_errors = []
    try:
        client = login_garmin()
        logger.info("Garmin login successful.")

        today = datetime.date.today()
        date_range = [today - datetime.timedelta(days=i) for i in range(3)]

        for sync_date in reversed(date_range):
            sync_date_str = sync_date.isoformat()
            logger.info(f"Fetching data for {sync_date_str}...")
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
            except Exception as e:
                error_msg = f"Failed to fetch data for {sync_date_str}: {e}"
                logger.error(error_msg)
                sync_errors.append(error_msg)
                continue

        try:
            sync_activities(client)
        except Exception as e:
            error_msg = f"Failed to sync activities: {e}"
            logger.error(error_msg)
            sync_errors.append(error_msg)

        if sync_errors:
            logger.warning(f"Sync completed with {len(sync_errors)} error(s).")
        else:
            logger.info("Sync completed successfully with no errors.")

        # Trigger graph sync in backend
        trigger_backend_sync()

    except Exception as e:
        import traceback
        logger.error(f"Critical sync error: {e}")
        logger.error(traceback.format_exc())


def main():
    logger.info("Worker Garmin started.")
    time.sleep(10)

    sync_interval_min = int(os.getenv("GARMIN_SYNC_INTERVAL_MIN", "30"))
    schedule.every(sync_interval_min).minutes.do(run_sync)
    logger.info(f"Scheduled Garmin sync every {sync_interval_min} minutes")

    run_sync()

    while True:
        schedule.run_pending()
        time.sleep(60)


if __name__ == "__main__":
    main()
