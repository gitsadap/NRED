from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
import json
import os
import uuid
from app.config import settings
from app.logging_config import logger
from app.security.config_validation import validate_security_settings

from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import OperationalError, DBAPIError
import socket

def _parse_cors_allow_origins(value: str) -> list[str]:
    raw = (value or "").strip()
    if not raw:
        return []
    if raw == "*":
        return ["*"]
    if raw.startswith("["):
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                return [str(o).strip() for o in parsed if str(o).strip()]
        except Exception:
            pass
    return [o.strip() for o in raw.split(",") if o.strip()]


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # Basic hardening headers
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")

        # Only set HSTS when served over HTTPS (avoid breaking local HTTP dev)
        if request.url.scheme == "https":
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")

        # Prevent caching admin pages (tokens live client-side; avoid caching sensitive admin HTML)
        if request.url.path.startswith("/admin"):
            response.headers.setdefault("Cache-Control", "no-store")

        # CSP can break built-in API docs UIs; skip for docs/redoc/openapi
        if not (
            request.url.path.startswith("/api/docs")
            or request.url.path.startswith("/api/redoc")
            or request.url.path.startswith("/openapi.json")
        ):
            is_admin_page = request.url.path.startswith("/admin")
            csp = (
                "default-src 'self'; "
                "base-uri 'self'; "
                "form-action 'self'; "
                "object-src 'none'; "
                "frame-ancestors 'self'; "
                "img-src 'self' data: https:; "
                "font-src 'self' data: https://fonts.gstatic.com; "
                "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://unpkg.com https://cdn.jsdelivr.net; "
                "script-src 'self' 'unsafe-inline' "
                + ("" if is_admin_page else "'unsafe-eval' ")
                + "https://cdn.tailwindcss.com https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://unpkg.com; "
                + ("worker-src 'self'; " if is_admin_page else "worker-src 'self' blob:; ")
                + "connect-src 'self' https:; "
                + "frame-src 'self' https://www.youtube.com https://www.youtube-nocookie.com; "
            )
            response.headers.setdefault("Content-Security-Policy", csp)

        return response


def _is_db_connectivity_error(exc: Exception) -> bool:
    if isinstance(exc, BaseExceptionGroup):
        for sub_exc in exc.exceptions:
            if isinstance(sub_exc, Exception) and _is_db_connectivity_error(sub_exc):
                return True
        return False
    if isinstance(exc, (OperationalError, socket.gaierror, ConnectionError, TimeoutError, OSError)):
        return True
    # Walk chained exceptions to catch wrapped asyncpg/socket errors.
    cursor = exc.__cause__ or exc.__context__
    depth = 0
    while cursor is not None and depth < 6:
        if isinstance(cursor, (OperationalError, socket.gaierror, ConnectionError, TimeoutError, OSError)):
            return True
        cursor = cursor.__cause__ or cursor.__context__
        depth += 1
    return False


class DatabaseErrorMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            return await call_next(request)
        except Exception as exc:
            if not _is_db_connectivity_error(exc):
                raise

            request_id = getattr(request.state, "request_id", "-")
            logger.error(
                "Database connectivity failure on %s %s (request_id=%s)",
                request.method,
                request.url.path,
                request_id,
                exc_info=settings.debug,
            )

            if request.url.path.startswith("/api") or request.url.path.startswith("/admin/api"):
                return JSONResponse(
                    status_code=503,
                    content={"detail": "Service temporarily unavailable", "request_id": request_id},
                )

            return HTMLResponse(
                """
                <!doctype html>
                <html lang="en">
                <head><meta charset="utf-8"><title>Service Unavailable</title></head>
                <body style="font-family: system-ui, sans-serif; padding: 2rem;">
                    <h1>Service temporarily unavailable</h1>
                    <p>Please try again shortly.</p>
                </body>
                </html>
                """,
                status_code=503,
            )


def _service_unavailable_response(request: Request) -> HTMLResponse | JSONResponse:
    request_id = getattr(request.state, "request_id", "-")
    if request.url.path.startswith("/api") or request.url.path.startswith("/admin/api"):
        return JSONResponse(
            status_code=503,
            content={"detail": "Service temporarily unavailable", "request_id": request_id},
        )
    return HTMLResponse(
        """
        <!doctype html>
        <html lang="en">
        <head><meta charset="utf-8"><title>Service Unavailable</title></head>
        <body style="font-family: system-ui, sans-serif; padding: 2rem;">
            <h1>Service temporarily unavailable</h1>
            <p>Please try again shortly.</p>
        </body>
        </html>
        """,
        status_code=503,
    )

app = FastAPI(
    title="Dep. Natural Resources & Environment",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

app.add_middleware(RequestIdMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(DatabaseErrorMiddleware)


@app.exception_handler(OperationalError)
@app.exception_handler(DBAPIError)
@app.exception_handler(OSError)
@app.exception_handler(Exception)
async def database_unavailable_handler(request: Request, exc: Exception):
    if _is_db_connectivity_error(exc):
        logger.error(
            "Database exception handled on %s %s (request_id=%s)",
            request.method,
            request.url.path,
            getattr(request.state, "request_id", "-"),
            exc_info=settings.debug,
        )
        return _service_unavailable_response(request)
    logger.error(
        "Unhandled exception on %s %s (request_id=%s)",
        request.method,
        request.url.path,
        getattr(request.state, "request_id", "-"),
        exc_info=settings.debug,
    )
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})

cors_allow_origins = _parse_cors_allow_origins(settings.cors_allow_origins)
cors_allow_credentials = bool(settings.cors_allow_credentials)
if cors_allow_origins == ["*"]:
    # Spec: wildcard origin cannot be used with credentials.
    cors_allow_credentials = False

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_allow_origins,
    allow_credentials=cors_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)


from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent

# Mount Static Files with proper error handling
static_dirs = [
    ("assets", "public/assets"),
    ("uploads", "public/uploads"),
    ("static", "static"),
    ("docs", "docs")
]

for mount_point, directory in static_dirs:
    abs_dir = BASE_DIR / directory
    if abs_dir.exists():
        app.mount(f"/{mount_point}", StaticFiles(directory=str(abs_dir)), name=mount_point)
        logger.info(f"Mounted static directory: {abs_dir} -> /{mount_point}")
    else:
        logger.warning(f"Static directory not found: {directory}")

# Templates
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# Import routers
from app.routers import public, appeals, admin, api, chatbot, auth
# Redirect routes
from fastapi.responses import RedirectResponse

@app.get("/admin")
async def redirect_admin():
    return RedirectResponse(url="/admin/")

app.include_router(auth.router)
app.include_router(admin.dashboard_router)
app.include_router(admin.teacher_router)
app.include_router(admin.router)
app.include_router(appeals.router)
app.include_router(api.router)
app.include_router(chatbot.router)
app.include_router(public.router)  # Public router has catch-all, so it MUST be last

@app.on_event("startup")
async def startup_event():
    logger.info("Application starting up...")

    issues = validate_security_settings(settings)
    for issue in issues:
        if settings.debug:
            logger.warning(f"[SECURITY WARNING] {issue}")
        else:
            logger.error(f"[SECURITY CONFIG ERROR] {issue}")
    if issues and not settings.debug:
        raise RuntimeError("Refusing to start with insecure configuration. Fix environment variables and restart.")

    logger.info("Routes initialized:")
    for route in app.routes:
        logger.info(f" - {route.path} [{route.name}]")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Application shutting down...")

if __name__ == "__main__":
    import uvicorn
    logger.info(f"Starting server on {settings.host}:{settings.port}")
    uvicorn.run(
        "main:app", 
        host=settings.host, 
        port=settings.port, 
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )
