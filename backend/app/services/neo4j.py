import os
import logging
from typing import Any

from neo4j import GraphDatabase

logger = logging.getLogger("neo4j")

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")


class Neo4jService:
    def __init__(self):
        self.driver = None
        try:
            self.driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
            logger.info("Neo4j driver initialized.")
        except Exception as e:
            logger.error(f"Neo4j driver init failed: {e}")

    def is_healthy(self) -> bool:
        if self.driver is None:
            return False
        try:
            self.driver.verify_connectivity()
            return True
        except Exception as e:
            logger.warning(f"Neo4j health check failed: {e}")
            return False

    def sync_activities(self, activities: list[dict[str, Any]]):
        if not self.driver:
            logger.warning("Neo4j driver not available, skipping sync")
            return
        with self.driver.session() as session:
            for act in activities:
                session.run(
                    """
                    MERGE (a:Activity {id: $id})
                    SET a.type = $type,
                        a.name = $name,
                        a.start_time = $start_time,
                        a.duration_sec = $duration_sec,
                        a.distance_meters = $distance_meters,
                        a.avg_hr = $avg_hr,
                        a.max_hr = $max_hr,
                        a.avg_pace = $avg_pace,
                        a.calories = $calories
                    """,
                    id=act.get("activity_id"),
                    type=act.get("activity_type"),
                    name=act.get("activity_name"),
                    start_time=str(act.get("start_time")),
                    duration_sec=act.get("duration_sec"),
                    distance_meters=float(act.get("distance_meters")) if act.get("distance_meters") is not None else None,
                    avg_hr=act.get("avg_hr"),
                    max_hr=act.get("max_hr"),
                    avg_pace=act.get("avg_pace"),
                    calories=act.get("calories"),
                )
        logger.info(f"Synced {len(activities)} activities to Neo4j.")

    def sync_health_daily(self, records: list[dict[str, Any]]):
        if not self.driver:
            logger.warning("Neo4j driver not available, skipping sync")
            return
        with self.driver.session() as session:
            for rec in records:
                session.run(
                    """
                    MERGE (d:DailyHealth {date: $date})
                    SET d.sleep_hours = $sleep_hours,
                        d.sleep_score = $sleep_score,
                        d.resting_hr = $resting_hr,
                        d.hrv_status = $hrv_status,
                        d.stress_level = $stress_level,
                        d.body_battery_max = $body_battery_max,
                        d.body_battery_min = $body_battery_min
                    """,
                    date=str(rec.get("date")),
                    sleep_hours=float(rec.get("sleep_hours")) if rec.get("sleep_hours") is not None else None,
                    sleep_score=rec.get("sleep_score"),
                    resting_hr=rec.get("resting_hr"),
                    hrv_status=rec.get("hrv_status"),
                    stress_level=rec.get("stress_level"),
                    body_battery_max=rec.get("body_battery_max"),
                    body_battery_min=rec.get("body_battery_min"),
                )
        logger.info(f"Synced {len(records)} daily health records to Neo4j.")

    def get_graph_data(self, limit: int = 100) -> dict[str, Any]:
        if not self.driver:
            return {"nodes": [], "edges": []}
        with self.driver.session() as session:
            result = session.run(
                """
                MATCH (n)
                OPTIONAL MATCH (n)-[r]->(m)
                RETURN n, r, m
                LIMIT $limit
                """,
                limit=limit,
            )
            nodes = {}
            edges = []
            for record in result:
                node = record["n"]
                if node.element_id not in nodes:
                    nodes[node.element_id] = {
                        "id": node.element_id,
                        "labels": list(node.labels),
                        "properties": dict(node),
                    }
                rel = record["r"]
                target = record["m"]
                if rel and target:
                    if target.element_id not in nodes:
                        nodes[target.element_id] = {
                            "id": target.element_id,
                            "labels": list(target.labels),
                            "properties": dict(target),
                        }
                    edges.append({
                        "source": node.element_id,
                        "target": target.element_id,
                        "type": rel.type,
                        "properties": dict(rel),
                    })
            return {"nodes": list(nodes.values()), "edges": edges}

    def close(self):
        if self.driver:
            self.driver.close()
            logger.info("Neo4j driver closed.")


# Global singleton instance
neo4j_service = Neo4jService()
