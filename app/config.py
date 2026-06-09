utf-8import os
from typing import Optional
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    
    database_url: str
    supabase_password: Optional[str] = None
    supabase: Optional[str] = None
    
    
    serp_api_key: str
    
    
    debug: bool = True
    log_level: str = "INFO"
    host: str = "0.0.0.0"
    port: int = 8099

    
    cors_allow_origins: str = "*"
    cors_allow_credentials: bool = False
    
    
    node_red_url: str = "http://10.10.58.21/nodered/api/chat"
    
    
    upload_dir: str = "uploads"
    max_file_size: int = 10485760  
    
    
    secret_key: str = "super-secret-key-please-change-in-env"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60  

    
    auth_rate_limit_max_attempts: int = 10
    auth_rate_limit_window_seconds: int = 900  
    auth_rate_limit_block_seconds: int = 900   
    
    
    admin_username: str = "admin"
    admin_password: str = "admin123" 
    
    
    ldap_server: str = "ldap://10.10.10.71"
    ldap_domain: str = "nu.local"
    ldap_timeout: int = 10
    ldap_require_tls: Optional[bool] = None  
    ldap_tls_validate: Optional[str] = None  
    ldap_tls_ca_cert_file: Optional[str] = None
    
    admin_users_list: str = "admin,user1,gitsadap"
    
    
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

    
    allow_unsafe_pickle_load: bool = False
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
