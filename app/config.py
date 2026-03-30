import os
from typing import Optional
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # Database Configuration
    database_url: str
    supabase_password: Optional[str] = None
    supabase: Optional[str] = None
    
    # External API Keys
    serp_api_key: str
    
    # Application Settings
    debug: bool = True
    log_level: str = "INFO"
    host: str = "0.0.0.0"
    port: int = 8099
    
    # External Services
    node_red_url: str = "http://10.10.58.21/nodered/api/chat"
    
    # File Upload Settings
    upload_dir: str = "uploads"
    max_file_size: int = 10485760  # 10MB
    
    # Security
    secret_key: str
    
    groq_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

@lru_cache()
def get_settings() -> Settings:
    return Settings()

# Global settings instance
settings = get_settings()
