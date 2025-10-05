from fastapi import FastAPI
from iroko.storage import neo4j_db
from iroko.cypher.routers import cypher
from iroko.auth.router import router as auth_router
from iroko.auth.init import initialize_auth_system
from iroko.config import app_settings  # Add this import
from fastapi.middleware.cors import CORSMiddleware
import os

# Get base path from environment or default to /api
BASE_PATH = os.getenv("BASE_PATH", app_settings.base_path)  # Use app_settings

app = FastAPI(
    title="Iroko API",
    version="0.1.0",
    root_path=BASE_PATH
)

# CORS Configuration - use settings from app_settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=app_settings.cors_origins,  # Use app_settings
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(cypher.router, prefix="/v1")
app.include_router(auth_router, prefix="/v1")

@app.on_event("startup")
async def startup_event():
    if app_settings.app_env != "test":  # Use app_settings
        await neo4j_db.get_session()  # Test Neo4j connection
        await initialize_auth_system()  # Initialize auth system

@app.on_event("shutdown")
async def shutdown_event():
    await neo4j_db.close()