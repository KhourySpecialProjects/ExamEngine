from fastapi import FastAPI
from src.api.routes import schedule
from src.api.routes import datasets
from src.api.routes import auth

app = FastAPI(title="Exam Scheduler API", version="1.0")

# TODO Initialize DB 
app.include_router(schedule.router)
app.include_router(datasets.router)
app.include_router(auth.router)

@app.get("/")
def root():
    return {"message": "Exam Scheduler API is running"}
