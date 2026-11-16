"""
FastAPI Application Entry Point (app/main.py)
Space Consultant – Meta Ads + DoubleTick Lead Automation Platform
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import SessionLocal
from app.routers import campaigns, dashboard, doubletick, leads, messages, meta, webhooks
from app.security.auth import rate_limiter
from app.utils.logger import get_logger
from app.utils.seed_data import init_and_seed_db
from app.workers.followup_worker import followup_daemon

logger = get_logger("main")

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "Production-ready Meta Instant Lead Ads + DoubleTick WhatsApp Business API "
        "Campaign-Wise Automation Platform for Space Consultant."
    ),
)

# Secure CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["*"],
)


# Sliding-Window Rate Limiting Middleware
@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    client_ip = request.client.host if request.client else "127.0.0.1"
    if not rate_limiter.is_allowed(client_ip):
        return JSONResponse(
            status_code=429,
            content={
                "status": "error",
                "detail": "Rate limit exceeded. Please try again in a minute.",
            },
        )
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    return response


@app.on_event("startup")
def on_startup():
    db = SessionLocal()
    try:
        init_and_seed_db(db=db, seed_sample_leads=True)
        logger.info("Database schema verified and Space Consultant initial configurations ready.")
    finally:
        db.close()

    if settings.FOLLOWUP_WORKER_ENABLED and settings.APP_ENV != "test":
        followup_daemon.start()


@app.on_event("shutdown")
def on_shutdown():
    followup_daemon.stop()


# Register All Routers
app.include_router(dashboard.router)
app.include_router(meta.router)
app.include_router(doubletick.router)
app.include_router(campaigns.router)
app.include_router(leads.router)
app.include_router(messages.router)
app.include_router(webhooks.router)


@app.get("/")
def root():
    return {
        "application": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "health_endpoint": "/api/health",
        "docs_endpoint": "/docs",
    }
