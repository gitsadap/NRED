from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
import os
from app.config import settings
from app.logging_config import logger

app = FastAPI(
    title="Dep. Natural Resources & Environment",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

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
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# Import routers
from app.routers import public, appeals, admin, api #, chatbot
# Redirect routes
from fastapi.responses import RedirectResponse

@app.get("/admin")
async def redirect_admin():
    return RedirectResponse(url="/admin/")

app.include_router(admin.router)
app.include_router(appeals.router)
app.include_router(api.router)
# app.include_router(chatbot.router)
app.include_router(public.router)  # Public router has catch-all, so it MUST be last

@app.on_event("startup")
async def startup_event():
    logger.info("Application starting up...")
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
