from fastapi import FastAPI
from src.api.routes import schedule

app = FastAPI(title="Exam Scheduler API", version="1.0")

app.include_router(schedule.router)

@app.get("/")
def root():
    return {"message": "Exam Scheduler API is running"}
