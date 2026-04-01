from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import admin, auth, datasets, schedule
from src.core.config import get_settings
from src.core.database import init_db


settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler - runs on startup and shutdown"""
    # Startup
    init_db()

    yield  # Server runs here


# Disable docs in production
_docs_url = None if settings.environment == "production" else "/docs"
_redoc_url = None if settings.environment == "production" else "/redoc"

# Create app with lifespan
app = FastAPI(title="Exam Scheduler API", version="1.0", lifespan=lifespan, docs_url=_docs_url, redoc_url=_redoc_url)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(schedule.router, prefix="/api")
app.include_router(datasets.router, prefix="/api")
app.include_router(auth.router, prefix="/api")
app.include_router(admin.router, prefix="/api")


@app.get("/")
def root():
    return {
        "message": "Exam Scheduler API is running",
        "environment": settings.environment,
    }


@app.get("/health")
def health():
    return {"status": "ok"}
