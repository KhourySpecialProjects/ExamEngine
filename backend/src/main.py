import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.api.routes import schedule
from src.api.routes import datasets
from src.api.routes import auth

app = FastAPI(title="Exam Scheduler API", version="1.0")

# Allow CORS from the frontend during development. Set FRONTEND_URL in env for prod.
frontend_origin = os.getenv("FRONTEND_URL", "http://localhost:3000")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend_origin, "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# TODO Initialize DB 
app.include_router(schedule.router)
app.include_router(datasets.router)
app.include_router(auth.router)

@app.get("/")
def root():
    return {"message": "Exam Scheduler API is running"}
