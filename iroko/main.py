from fastapi import FastAPI
from contextlib import asynccontextmanager
from iroko.storage import neo4j_db
from iroko.cypher.routers import cypher
from iroko.auth.router import router as auth_router
from iroko.auth.init import initialize_auth_system
from iroko.evals.router import router as evals_router
from iroko.tasks.router import router as crawler_router
from iroko.tasks.manager import crawler_manager
from iroko.evals.service import eval_service
from iroko.config import app_settings
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.gzip import GZipMiddleware

import os

from iroko.database import init_db, close_db  # Import central database functions


from .logging_config import setup_logging
import logging

# Setup logging first
setup_logging()
logger = logging.getLogger('iroko-cris')

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info(f"Starting Iroko API in {app_settings.app_env} environment")
    
    if app_settings.app_env != "test":
        try:
            await neo4j_db.get_session()
            
            await init_db()
            
            await initialize_auth_system()
            
            await crawler_manager.auto_discover_tasks()
            logger.info("Crawler manager initialized with auto-discovered tasks")

            await eval_service.load_methodologies()
            await eval_service.validate_methodology_rules()
            # if app_settings.app_env == "production":
            await eval_service.preload_all_methodology_rules()

            logger.info("All services initialized successfully")
        except Exception as e:
            logger.error(f"Service initialization failed: {e}")
            raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down Iroko API")
    await crawler_manager.shutdown()
    await neo4j_db.close()
    await close_db()

# Get base path from environment or default to /api
BASE_PATH = os.getenv("BASE_PATH", app_settings.base_path)

app = FastAPI(
    title="Iroko API",
    version="0.1.0",
    root_path=BASE_PATH,
    lifespan=lifespan,
    docs_url="/docs" if app_settings.app_env != "production" else None,
    redoc_url="/redoc" if app_settings.app_env != "production" else None
)


# Security Middleware
if app_settings.app_env == "production":
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=[
            "sceiba.reduniv.edu.cu",
            "sceiba.mes.gob.cu",
        ]
    )

# Compression Middleware
app.add_middleware(GZipMiddleware, minimum_size=1000)

# CORS Configuration - use settings from app_settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=app_settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "Accept",
        "Origin",
        "X-Requested-With",
        "X-CSRF-Token",
        "Access-Control-Allow-Headers",
        "Access-Control-Request-Method",
        "Access-Control-Request-Headers"
    ],
    expose_headers=[
        "Content-Range",
        "X-Content-Range",
        "X-Total-Count"
    ],
    max_age=600,  # Cache preflight requests for 10 minutes
)

# Include routers

app.include_router(cypher.router, prefix="/v1")
app.include_router(auth_router, prefix="/v1")
app.include_router(evals_router, prefix="/v1")
app.include_router(crawler_router, prefix="/v1")


# Add CORS preflight handler for all routes
@app.options("/{rest_of_path:path}")
async def preflight_handler(rest_of_path: str) -> dict:
    return {"message": "CORS preflight"}



# Health check with CORS headers
@app.get("/health")
async def health_check():
    return {"status": "ok", "environment": app_settings.app_env}