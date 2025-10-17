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
    
    # CORS Configuration
    cors_origins: List[str] = [
        "http://localhost:3000",
        "http://localhost:8000", 
        "http://localhost:4200",
        "http://localhost:8080",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8000",
        "http://127.0.0.1:4200",
        "http://127.0.0.1:8080",
    ]
    
    # Production domain - will be added conditionally
    production_domain: str = "https://sceiba.mes.gob.cu"
    
    # Admin User (for initial setup)
    admin_email: Optional[str] = "admin@iroko.cu"
    admin_password: Optional[str] = "admin123"
    admin_full_name: Optional[str] = "System Administrator"

    log_to_file: bool = True
    log_file_path: str = "iroko.log"
    log_level: str = "INFO"  # Add log level configuration
    json_logs: bool = False  # Use JSON logging format
    
    # Container detection
    container_env: bool = False
    
    @property
    def allowed_origins(self) -> List[str]:
        """Get CORS origins based on environment"""
        origins = self.cors_origins.copy()
        
        # Add production domain in production environment
        if self.app_env == "production":
            origins.extend([
                self.production_domain,
                "https://sceiba.reduniv.edu.cu",  # Add www subdomain if needed
            ])
        else:
            # In development, allow common dev origins with HTTPS variants
            origins.extend([
                "https://localhost:3000",
                "https://localhost:4200", 
                "https://127.0.0.1:3000",
                "https://127.0.0.1:4200",
            ])
        
        # Remove duplicates and return
        return list(set(origins))

    class Config:
        env_file = ".env"
        extra = "ignore"

app_settings = AppSettings()