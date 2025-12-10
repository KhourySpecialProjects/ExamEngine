from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

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

# Add validation error handler to log details
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Log validation errors for debugging."""
    print(f"[Validation Error] Path: {request.url.path}")
    print(f"[Validation Error] Errors: {exc.errors()}")
    
    # Convert errors to JSON-serializable format
    errors = []
    for error in exc.errors():
        serializable_error = {}
        for key, value in error.items():
            # Convert bytes to string if needed
            if isinstance(value, bytes):
                serializable_error[key] = value.decode('utf-8', errors='replace')
            else:
                serializable_error[key] = value
        errors.append(serializable_error)
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": errors},
        headers={
            "Access-Control-Allow-Origin": settings.frontend_url,
            "Access-Control-Allow-Credentials": "true",
        },
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
