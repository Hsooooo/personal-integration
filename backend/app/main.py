import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncEngine

from app.routers import activities, graph, garmin, auth, user
from app.database import engine, Base
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
    # Create SQLAlchemy tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # Init legacy raw tables (for worker compatibility)
    pg_service.init_tables()
    # Setup Neo4j constraints
    neo4j_service.setup_constraints()
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

# v1 routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(user.router, prefix="/api/v1/users", tags=["users"])
app.include_router(activities.router, prefix="/api/v1/activities", tags=["activities"])
app.include_router(graph.router, prefix="/api/v1/graph", tags=["graph"])
app.include_router(garmin.router, prefix="/api/v1/garmin", tags=["garmin"])


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
