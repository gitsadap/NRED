from fastapi import HTTPException
from app.logging_config import logger
from typing import Any, Dict, Optional
import traceback

class DatabaseError(Exception):
    """Custom exception for database errors"""
    pass

class ExternalServiceError(Exception):
    """Custom exception for external service errors"""
    pass

class ValidationError(Exception):
    """Custom exception for validation errors"""
    pass

def handle_database_error(func):
    """Decorator to handle database errors"""
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Database error in {func.__name__}: {e}")
            logger.error(traceback.format_exc())
            raise HTTPException(status_code=500, detail="Database operation failed")
    return wrapper

def handle_external_service_error(func):
    """Decorator to handle external service errors"""
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            logger.error(f"External service error in {func.__name__}: {e}")
            raise HTTPException(status_code=503, detail="External service unavailable")
    return wrapper

def create_error_response(message: str, status_code: int = 400, details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Create standardized error response"""
    response = {
        "status": "error",
        "message": message,
        "status_code": status_code
    }
    if details:
        response["details"] = details
    return response

def log_error(message: str, exception: Exception, context: Optional[Dict[str, Any]] = None):
    """Log error with context"""
    error_msg = f"{message}: {str(exception)}"
    if context:
        error_msg += f" | Context: {context}"
    logger.error(error_msg)
    logger.error(traceback.format_exc())
