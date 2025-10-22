import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.api.routes import schedule
from src.api.routes import datasets
from src.api.routes import auth
from src.schemas.db import Base
from dotenv import load_dotenv 
from sqlalchemy import create_engine
load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler - runs on startup and shutdown"""
    # Startup
    db_url = os.getenv("DATABASE_URL", "sqlite:///./dev.db")
    connect_args = {"check_same_thread": False} if db_url.startswith("sqlite") else {}
    
    engine = create_engine(db_url, connect_args=connect_args, echo=False)
    Base.metadata.create_all(bind=engine)
    
    yield  # Server runs here
    

# Create app with lifespan
app = FastAPI(
    title="Exam Scheduler API", 
    version="1.0",
    lifespan=lifespan
)

# CORS
frontend_origin = os.getenv("FRONTEND_URL", "http://localhost:3000")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend_origin, "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(schedule.router)
app.include_router(datasets.router)
app.include_router(auth.router)

@app.get("/")
def root():
    return {"message": "Exam Scheduler API is running"}
