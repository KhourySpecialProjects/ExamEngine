from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import IntegrityError

from src.api.routes import admin, auth, datasets, schedule
from src.core.config import get_settings
from src.core.database import SessionLocal, init_db
from src.repo.user import UserRepo
from src.utils.password import get_password_hash


settings = get_settings()


def seed_initial_admin() -> None:
    """Create the initial admin from settings if no admin exists.

    Development-only: guarded so production never auto-creates a
    default-password admin account. Idempotent via the admin count check,
    and race-safe against concurrent workers via IntegrityError rollback.
    """
    if settings.environment != "development":
        return

    db = SessionLocal()
    try:
        user_repo = UserRepo(db)
        if user_repo.count_admins() > 0:
            return
        user_repo.create_user(
            name="Administrator",
            email=settings.admin_email,
            password_hash=get_password_hash(settings.admin_password),
            role="admin",
            status="approved",
        )
    except IntegrityError:
        # Another worker seeded the admin concurrently; safe to ignore.
        db.rollback()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler - runs on startup and shutdown"""
    # Startup
    init_db()
    seed_initial_admin()

    yield  # Server runs here


# Create app with lifespan
app = FastAPI(title="Exam Scheduler API", version="1.0", lifespan=lifespan)

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
