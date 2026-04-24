import os
import logging
import re
from typing import Any
from datetime import datetime

from neo4j import GraphDatabase

logger = logging.getLogger("neo4j")

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")

# Graph schema per PRD
NODE_LABELS = ["Person", "Activity", "Lap", "TrainingBlock", "Race", "BodyState"]
EDGE_TYPES = ["PERFORMED", "HAS_LAP", "FOLLOWS", "PART_OF", "PREPARES_FOR", "INFLUENCED_BY", "SIMILAR_EFFORT"]

_READ_ONLY_PATTERN = re.compile(
    r"^\s*(MATCH|OPTIONAL\s+MATCH|RETURN|UNWIND|WITH|CALL|COUNT|COLLECT|LIMIT|SKIP|ORDER\s+BY|WHERE|AS)\s+",
    re.IGNORECASE,
)
_WRITE_KEYWORDS = re.compile(
    r"\b(CREATE|DELETE|DETACH\s+DELETE|SET|REMOVE|MERGE|DROP|CALL\s+\{.*\}\s+IN\s+TRANSACTIONS)\b",
    re.IGNORECASE,
)


def _validate_readonly(cypher: str) -> bool:
    # Reject obvious write keywords
    if _WRITE_KEYWORDS.search(cypher):
        return False
    # Allow only read-only constructs
    lines = cypher.strip().split(";")
    for stmt in lines:
        stmt = stmt.strip()
        if not stmt:
            continue
        if not _READ_ONLY_PATTERN.match(stmt):
            return False
    return True


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

    def setup_constraints(self):
        """Create constraints if not exist. Idempotent."""
        if not self.driver:
            return
        constraints = [
            "CREATE CONSTRAINT person_name IF NOT EXISTS FOR (p:Person) REQUIRE p.name IS UNIQUE",
            "CREATE CONSTRAINT activity_id IF NOT EXISTS FOR (a:Activity) REQUIRE a.id IS UNIQUE",
            "CREATE CONSTRAINT lap_key IF NOT EXISTS FOR (l:Lap) REQUIRE (l.activityId, l.index) IS UNIQUE",
            "CREATE CONSTRAINT body_date IF NOT EXISTS FOR (b:BodyState) REQUIRE b.date IS UNIQUE",
            "CREATE CONSTRAINT block_key IF NOT EXISTS FOR (t:TrainingBlock) REQUIRE (t.year, t.week) IS UNIQUE",
            "CREATE CONSTRAINT race_id IF NOT EXISTS FOR (r:Race) REQUIRE r.id IS UNIQUE",
        ]
        with self.driver.session() as session:
            for cql in constraints:
                try:
                    session.run(cql)
                except Exception as e:
                    logger.warning(f"Constraint creation skipped: {e}")
        logger.info("Neo4j constraints ensured.")

    def sync_activities(
        self,
        activities: list[dict[str, Any]],
        person_name: str = "한수",
        timezone: str = "Asia/Seoul",
    ):
        if not self.driver:
            logger.warning("Neo4j driver not available, skipping sync")
            return
        with self.driver.session() as session:
            # Ensure Person exists
            session.run(
                "MERGE (p:Person {name: $name}) SET p.timezone = $tz",
                name=person_name,
                tz=timezone,
            )
            for act in activities:
                aid = act.get("activity_id")
                # MERGE Activity
                session.run(
                    """
                    MERGE (a:Activity {id: $id})
                    SET a.type = $type,
                        a.name = $name,
                        a.startTime = $start_time,
                        a.distanceKm = $dist,
                        a.durationMin = $dur,
                        a.avgHr = $ahr,
                        a.maxHr = $mhr,
                        a.avgPace = $pace,
                        a.elevation = $elev
                    """,
                    id=aid,
                    type=act.get("activity_type"),
                    name=act.get("activity_name"),
                    start_time=str(act.get("start_time")) if act.get("start_time") else None,
                    dist=round(float(act.get("distance_meters") or 0) / 1000, 2) if act.get("distance_meters") else None,
                    dur=round(float(act.get("duration_sec") or 0) / 60, 2) if act.get("duration_sec") else None,
                    ahr=act.get("avg_hr"),
                    mhr=act.get("max_hr"),
                    pace=act.get("avg_pace"),
                    elev=act.get("elevation_gain"),
                )
                # Link Person -> Activity
                session.run(
                    """
                    MATCH (p:Person {name: $pname})
                    MATCH (a:Activity {id: $aid})
                    MERGE (p)-[:PERFORMED]->(a)
                    """,
                    pname=person_name,
                    aid=aid,
                )
                # TrainingBlock (year-week)
                st = act.get("start_time")
                if st:
                    try:
                        dt = datetime.fromisoformat(str(st).replace("Z", "+00:00"))
                        year, week, _ = dt.isocalendar()
                        session.run(
                            """
                            MERGE (t:TrainingBlock {year: $year, week: $week})
                            SET t.name = $name
                            WITH t
                            MATCH (a:Activity {id: $aid})
                            MERGE (a)-[:PART_OF]->(t)
                            """,
                            year=year,
                            week=week,
                            name=f"{year}-W{week:02d}",
                            aid=aid,
                        )
                    except Exception:
                        pass
                # Follows edge (chronological)
                session.run(
                    """
                    MATCH (a:Activity {id: $aid})
                    MATCH (prev:Activity)
                    WHERE prev.id <> $aid AND prev.startTime < a.startTime
                    WITH prev ORDER BY prev.startTime DESC LIMIT 1
                    MERGE (prev)-[:FOLLOWS]->(a)
                    """,
                    aid=aid,
                )
        logger.info(f"Synced {len(activities)} activities to Neo4j.")

    def sync_laps(self, laps: list[dict[str, Any]]):
        if not self.driver:
            return
        with self.driver.session() as session:
            for lap in laps:
                aid = lap.get("activity_id")
                idx = lap.get("lap_index")
                session.run(
                    """
                    MERGE (l:Lap {activityId: $aid, index: $idx})
                    SET l.distanceKm = $dist,
                        l.durationSec = $dur,
                        l.avgPace = $pace,
                        l.avgHr = $ahr,
                        l.maxHr = $mhr
                    WITH l
                    MATCH (a:Activity {id: $aid})
                    MERGE (a)-[:HAS_LAP]->(l)
                    """,
                    aid=aid,
                    idx=idx,
                    dist=round(float(lap.get("distance_meters") or 0) / 1000, 2) if lap.get("distance_meters") else None,
                    dur=lap.get("duration_sec"),
                    pace=lap.get("avg_pace"),
                    ahr=lap.get("avg_hr"),
                    mhr=lap.get("max_hr"),
                )
        logger.info(f"Synced {len(laps)} laps to Neo4j.")

    def sync_health_daily(self, records: list[dict[str, Any]], person_name: str = "한수"):
        if not self.driver:
            logger.warning("Neo4j driver not available, skipping sync")
            return
        with self.driver.session() as session:
            for rec in records:
                session.run(
                    """
                    MERGE (b:BodyState {date: $date})
                    SET b.sleepHours = $sleep_hours,
                        b.sleepScore = $sleep_score,
                        b.restingHr = $resting_hr,
                        b.hrv = $hrv_status,
                        b.stress = $stress_level,
                        b.bodyBatteryMax = $body_battery_max,
                        b.bodyBatteryMin = $body_battery_min
                    WITH b
                    MATCH (p:Person {name: $pname})
                    MERGE (p)-[:HAS_STATE {date: $date}]->(b)
                    """,
                    date=str(rec.get("date")),
                    sleep_hours=float(rec.get("sleep_hours")) if rec.get("sleep_hours") is not None else None,
                    sleep_score=rec.get("sleep_score"),
                    resting_hr=rec.get("resting_hr"),
                    hrv_status=rec.get("hrv_status"),
                    stress_level=rec.get("stress_level"),
                    body_battery_max=rec.get("body_battery_max"),
                    body_battery_min=rec.get("body_battery_min"),
                    pname=person_name,
                )
                # Activity influenced by BodyState on same date
                session.run(
                    """
                    MATCH (b:BodyState {date: $date})
                    MATCH (a:Activity)
                    WHERE a.startTime STARTS WITH $date_prefix
                    MERGE (a)-[:INFLUENCED_BY]->(b)
                    """,
                    date=str(rec.get("date")),
                    date_prefix=str(rec.get("date")),
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

    def run_query(self, cypher: str, parameters: dict | None = None) -> dict[str, Any]:
        if not self.driver:
            raise RuntimeError("Neo4j driver not available")
        if not _validate_readonly(cypher):
            raise PermissionError("Only read-only Cypher queries are allowed")
        with self.driver.session() as session:
            result = session.run(cypher, parameters or {})
            keys = result.keys()
            data = [dict(zip(keys, record.values())) for record in result]
            return {"columns": keys, "data": data}

    def get_schema(self) -> dict[str, Any]:
        return {"node_labels": NODE_LABELS, "edge_types": EDGE_TYPES}

    def close(self):
        if self.driver:
            self.driver.close()
            logger.info("Neo4j driver closed.")


# Global singleton instance
neo4j_service = Neo4jService()
