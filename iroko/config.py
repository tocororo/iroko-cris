from pydantic_settings import BaseSettings
from typing import List, Optional
import secrets

class AppSettings(BaseSettings):
    # App Settings
    app_env: str = "development"
    base_path: str = "/api"
    fastapi_endpoint: str = "http://127.0.0.1:8000"
    
    # Neo4j Settings
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_username: str = "neo4j"
    neo4j_password: str = "password"
    neo4j_database: str = "iroko"
    
    # PostgreSQL Settings
    postgres_db: str = "iroko"
    postgres_user: str = "iroko_user"
    postgres_password: str = "iroko_password"
    database_url: str = "postgresql+asyncpg://iroko_user:iroko_password@postgres/iroko"
    
    # JWT Settings
    secret_key: str = "your-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 3000
    
    # CORS
    cors_origins: List[str] = ["http://localhost:3000", "http://localhost:8000"]
    
    # Admin User (for initial setup)
    admin_email: Optional[str] = "admin@iroko.cu"
    admin_password: Optional[str] = "admin123"
    admin_full_name: Optional[str] = "System Administrator"
    
    class Config:
        env_file = ".env"
        extra = "ignore"

app_settings = AppSettings()