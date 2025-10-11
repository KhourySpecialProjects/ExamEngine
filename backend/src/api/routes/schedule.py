from fastapi import APIRouter, UploadFile, File
from fastapi.responses import StreamingResponse
import pandas as pd
from backend.src.algorithms.dsatur_scheduler import DSATURExamGraph
from backend.src.algorithms.create_schedule import export_student_schedule
import io
import zipfile

router = APIRouter(prefix="/schedule", tags=["Scheduling"])


# This endpoint runs the scheduling algorithm and returns a summary and preview of results
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

# This endpoint runs the scheduling algorithm and returns downloadable CSVs in a ZIP
@router.post("/output")
async def post_output(census: UploadFile = File(...),
                      enrollment: UploadFile = File(...),
                      classrooms: UploadFile = File(...)):
    """Generate schedules and return a ZIP containing student_schedule_long.csv and student_schedule_wide.csv

    This mirrors the `/generate` endpoint but returns downloadable CSVs in a zip archive.
    """
    # Read uploaded CSVs
    census_df = pd.read_csv(io.BytesIO(await census.read()))
    enrollment_df = pd.read_csv(io.BytesIO(await enrollment.read()))
    classrooms_df = pd.read_csv(io.BytesIO(await classrooms.read()))

    # Run algorithm
    graph = DSATURExamGraph(census_df, enrollment_df, classrooms_df)
    graph.build_graph()
    graph.dsatur_color()
    graph.dsatur_schedule()
    df_schedule = graph.assign_rooms()

    # Use helper to get DataFrames (it also writes files to disk, but we will capture DataFrames returned)
    long_df, wide_df = export_student_schedule(graph, enrollment_df, df_schedule, base_name="student_schedule")

    # Convert DataFrames to CSV bytes
    long_buf = io.BytesIO()
    wide_buf = io.BytesIO()
    long_df.to_csv(long_buf, index=False)
    wide_df.to_csv(wide_buf, index=False)
    long_buf.seek(0)
    wide_buf.seek(0)

    # Create ZIP in-memory
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, mode="w", compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr("student_schedule_long.csv", long_buf.read())
        z.writestr("student_schedule_wide.csv", wide_buf.read())
    zip_buffer.seek(0)

    headers = {"Content-Disposition": "attachment; filename=student_schedules.zip"}
    return StreamingResponse(zip_buffer, media_type="application/zip", headers=headers)