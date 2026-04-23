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

    # CORS (comma-separated list or "*" for public APIs)
    cors_allow_origins: str = "*"
    cors_allow_credentials: bool = False
    
    # External Services
    node_red_url: str = "http://10.10.58.21/nodered/api/chat"
    
    # File Upload Settings
    upload_dir: str = "uploads"
    max_file_size: int = 10485760  # 10MB
    
    # Security / Auth
    secret_key: str = "super-secret-key-please-change-in-env"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60  # 1 hour (override via ACCESS_TOKEN_EXPIRE_MINUTES)

    # Login rate limiting (in-memory; tune for your environment)
    auth_rate_limit_max_attempts: int = 10
    auth_rate_limit_window_seconds: int = 900  # 15 minutes
    auth_rate_limit_block_seconds: int = 900   # 15 minutes
    
    # We will still keep the local admin override but add ldap options
    admin_username: str = "admin"
    admin_password: str = "admin123" # override in .env
    
    # LDAP Configuration
    ldap_server: str = "ldap://10.10.10.71"
    ldap_domain: str = "nu.local"
    ldap_timeout: int = 10
    ldap_require_tls: Optional[bool] = None  # default: True in production, False in debug
    ldap_tls_validate: Optional[str] = None  # CERT_REQUIRED / CERT_OPTIONAL / CERT_NONE
    ldap_tls_ca_cert_file: Optional[str] = None
    # Comma separated list of users who are allowed to login as admin via LDAP
    admin_users_list: str = "admin,user1,gitsadap"
    
    # External Databases for Authentication
    student_db_server: Optional[str] = None
    student_db_name: Optional[str] = None
    student_db_user: Optional[str] = None
    student_db_pass: Optional[str] = None

    staff_db_host: Optional[str] = None
    staff_db_name: Optional[str] = None
    staff_db_user: Optional[str] = None
    staff_db_pass: Optional[str] = None
    
    groq_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None

    # Unsafe deserialization (disabled by default). Only enable for trusted local migration.
    allow_unsafe_pickle_load: bool = False
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

@lru_cache()
def get_settings() -> Settings:
    return Settings()

# Global settings instance
settings = get_settings()
