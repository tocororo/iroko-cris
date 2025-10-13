from fastapi import FastAPI
from contextlib import asynccontextmanager
from iroko.storage import neo4j_db
from iroko.cypher.routers import cypher
from iroko.auth.router import router as auth_router
from iroko.auth.init import initialize_auth_system
from iroko.evals.router import router as evals_router
from iroko.evals.service import eval_service
from iroko.config import app_settings
from fastapi.middleware.cors import CORSMiddleware
import os

from iroko.database import init_db, close_db  # Import central database functions


import logging

from .logging_config import setup_logging

# Setup logging first
setup_logging()
logger = logging.getLogger('iroko-cris')




@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    if app_settings.app_env != "test":
        await neo4j_db.get_session()  # Test Neo4j connection
        await init_db()  # Initialize ALL database tables
        await initialize_auth_system()  # Initialize auth system
        await eval_service.load_methodologies()  # Load evaluation methodologies
    yield
    # Shutdown
    await neo4j_db.close()
    await close_db()

# Get base path from environment or default to /api
BASE_PATH = os.getenv("BASE_PATH", app_settings.base_path)

app = FastAPI(
    title="Iroko API",
    version="0.1.0",
    root_path=BASE_PATH,
    lifespan=lifespan
)

# CORS Configuration - use settings from app_settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=app_settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(cypher.router, prefix="/v1")
app.include_router(auth_router, prefix="/v1")
app.include_router(evals_router, prefix="/v1")