from fastapi import APIRouter, UploadFile, File
import pandas as pd
from backend.src.algorithms.dsatur_scheduler import DSATURExamGraph
import io

router = APIRouter(prefix="/schedule", tags=["Scheduling"])

@router.post("/generate")
async def generate_schedule(census: UploadFile = File(...),
                            enrollment: UploadFile = File(...),
                            classrooms: UploadFile = File(...)):
    # Read uploaded CSVs into DataFrames
    census_df = pd.read_csv(io.BytesIO(await census.read()))
    enrollment_df = pd.read_csv(io.BytesIO(await enrollment.read()))
    classrooms_df = pd.read_csv(io.BytesIO(await classrooms.read()))

    # Run algorithm
    graph = DSATURExamGraph(census_df, enrollment_df, classrooms_df)
    graph.build_graph()
    graph.dsatur_color()
    graph.dsatur_schedule()
    results = graph.assign_rooms()
    summary = graph.summary()

    # Return summary and top few rows
    return {
        "summary": summary,
        "preview": results.head(10).to_dict(orient="records")
    }
