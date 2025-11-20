from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import auth, datasets, schedule
from src.core.config import get_settings
from src.core.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler - runs on startup and shutdown"""
    # Startup
    init_db()

    yield  # Server runs here


# Create app with lifespan
app = FastAPI(title="Exam Scheduler API", version="1.0", lifespan=lifespan)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Get settings
settings = get_settings()

app.include_router(schedule.router)
app.include_router(datasets.router)
app.include_router(auth.router)


@app.get("/")
def root():
    return {
        "message": "Exam Scheduler API is running",
        "environment": settings.environment,
    }
