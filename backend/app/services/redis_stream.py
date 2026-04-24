import os
import logging
import redis

logger = logging.getLogger("redis_stream")

REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))

STREAM_NAME = "garmin-sync"
CONSUMER_GROUP = "garmin-workers"


class RedisStreamProducer:
    def __init__(self):
        self.client = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            db=REDIS_DB,
            decode_responses=True,
        )
        try:
            self.client.ping()
            logger.info("Redis producer connected.")
        except Exception as e:
            logger.warning(f"Redis producer connection failed: {e}")

    def publish_sync_job(self, user_id: int, sync_type: str = "full") -> str:
        message = {
            "user_id": str(user_id),
            "sync_type": sync_type,
        }
        msg_id = self.client.xadd(STREAM_NAME, message)
        logger.info(f"Published sync job {msg_id} for user {user_id} (type={sync_type})")
        return msg_id

    def publish_race_classify_job(
        self,
        user_id: int,
        activity_id: int,
        race_type: str,
        prep_weeks: int = 12,
    ) -> str:
        message = {
            "job_type": "race_classify",
            "user_id": str(user_id),
            "activity_id": str(activity_id),
            "race_type": race_type,
            "prep_weeks": str(prep_weeks),
        }
        msg_id = self.client.xadd(STREAM_NAME, message)
        logger.info(
            f"Published race classify job {msg_id} for activity {activity_id} "
            f"(type={race_type}, prep={prep_weeks}w)"
        )
        return msg_id

    def get_pending_count(self) -> int:
        try:
            info = self.client.xinfo_stream(STREAM_NAME)
            return info.get("length", 0)
        except redis.ResponseError:
            return 0


# Global singleton
redis_producer = RedisStreamProducer()
