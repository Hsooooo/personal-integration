import os
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import activities, graph, garmin
from app.services.postgres import pg_service
from app.services.neo4j import neo4j_service

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
)
logger = logging.getLogger("backend")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up backend...")
    pg_service.init_tables()
    yield
    logger.info("Shutting down backend...")
    pg_service.close()
    neo4j_service.close()


app = FastAPI(title="Personal Integration API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(activities.router, prefix="/api/activities", tags=["activities"])
app.include_router(graph.router, prefix="/api/graph", tags=["graph"])
app.include_router(garmin.router, prefix="/api/garmin", tags=["garmin"])


@app.get("/health")
def health_check():
    pg_ok = pg_service.is_healthy()
    neo4j_ok = neo4j_service.is_healthy()
    status = "ok" if (pg_ok and neo4j_ok) else "degraded"
    return {
        "status": status,
        "postgres": "ok" if pg_ok else "error",
        "neo4j": "ok" if neo4j_ok else "error",
    }


@app.get("/")
def root():
    return {"message": "Personal Integration API"}
