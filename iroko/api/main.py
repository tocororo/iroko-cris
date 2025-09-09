from fastapi import FastAPI
from iroko.storage import neo4j_db
from api.routers import cypher
from fastapi.middleware.cors import CORSMiddleware
import os

# Get base path from environment or default to /api
BASE_PATH = os.getenv("BASE_PATH", "/api")

app = FastAPI(
    title="Iroko API",
    version="0.1.0",
    root_path=BASE_PATH  # Critical for OpenAPI docs
)
# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(cypher.router, prefix="/v1")

@app.on_event("startup")
async def startup_event():
    if os.getenv("APP_ENV") != "test":
        await neo4j_db.get_session()  # Test connection

@app.on_event("shutdown")
async def shutdown_event():
    await neo4j_db.close()