import io
import uuid
import zipfile

import pandas as pd
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from src.algorithms.create_schedule import export_student_schedule
from src.algorithms.dsatur_scheduler import DSATURExamGraph
from src.schemas.db import Datasets, Users
from src.services.auth import get_current_user, get_session
from src.services.storage import storage_service


router = APIRouter(prefix="/schedule", tags=["schedules"])


def get_db():
    """Database session dependency"""
    db = get_session()
    try:
        yield db
    finally:
        db.close()


# This endpoint runs the scheduling algorithm and returns a summary and preview of results
@router.post("/generate")
async def generate_schedule(
    census: UploadFile = File(...),
    enrollment: UploadFile = File(...),
    classrooms: UploadFile = File(...),
):
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
    return {"summary": summary, "preview": results.head(10).to_dict(orient="records")}


# This endpoint runs the scheduling algorithm and returns downloadable CSVs in a ZIP
@router.post("/output")
async def post_output(
    census: UploadFile = File(...),
    enrollment: UploadFile = File(...),
    classrooms: UploadFile = File(...),
):
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
    long_df, wide_df = export_student_schedule(
        graph, enrollment_df, df_schedule, base_name="student_schedule"
    )

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


@router.post("/generate/{dataset_id}")
async def generate_schedule_from_dataset(
    dataset_id: str,
    max_per_day: int = 3,
    avoid_back_to_back: bool = True,
    max_days: int = 7,
    current_user: Users = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Generate complete schedule from a stored dataset

    Returns:
        Complete schedule with all exams, conflicts, and metadata
    """
    try:
        dataset = (
            db.query(Datasets)
            .filter(
                Datasets.dataset_id == uuid.UUID(dataset_id),
                Datasets.user_id == current_user.user_id,
            )
            .first()
        )

        if not dataset:
            raise HTTPException(404, "Dataset not found or access denied")

        files_data = {}
        for file_entry in dataset.file_paths:
            file_type = file_entry["type"]
            storage_key = file_entry["storage_key"]

            content = storage_service.download_file(storage_key)
            if not content:
                raise HTTPException(404, f"File not found in S3: {file_type}")

            files_data[file_type] = content

        census_df = pd.read_csv(io.BytesIO(files_data["courses"]))
        enrollment_df = pd.read_csv(io.BytesIO(files_data["enrollments"]))
        classrooms_df = pd.read_csv(io.BytesIO(files_data["rooms"]))

    except Exception as e:
        raise HTTPException(500, f"Error computing algorithm: {str(e)}") from e

    try:
        graph = DSATURExamGraph(census_df, enrollment_df, classrooms_df)
        graph.build_graph()
        graph.dsatur_color()
        graph.dsatur_schedule(
            max_per_day=max_per_day,
            avoid_back_to_back=avoid_back_to_back,
            max_days=max_days,
        )
        results_df = graph.assign_rooms()
        summary = graph.summary()

        total_conflicts, conflict_details, breakdown_df = (
            graph.count_schedule_conflicts()
        )
        fail_report = graph.fail_report()
        complete_schedule = results_df.to_dict(orient="records")
        calendar_data = _build_calendar_structure(results_df)

        return {
            "dataset_id": dataset_id,
            "dataset_name": dataset.dataset_name,
            "summary": summary,
            "conflicts": {
                "total": total_conflicts,
                "breakdown": breakdown_df.to_dict(orient="records")
                if not breakdown_df.empty
                else [],
                "details": {str(k): v for k, v in conflict_details.items()}
                if conflict_details
                else {},
            },
            "failures": fail_report.to_dict(orient="records")
            if not fail_report.empty
            else [],
            "schedule": {
                "complete": complete_schedule,
                "calendar": calendar_data,
                "total_exams": len(complete_schedule),
            },
            "parameters": {
                "max_per_day": max_per_day,
                "avoid_back_to_back": avoid_back_to_back,
                "max_days": max_days,
            },
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Schedule generation failed: {e}"
        ) from e


def _build_calendar_structure(results_df: pd.DataFrame) -> dict:
    """
    Convert schedule DataFrame to calendar structure

    Returns:
        {
            "Monday": {
                "9:00-11:00": [exam1, exam2, ...],
                "11:30-13:30": [...]
            },
            "Tuesday": {...}
        }
    """
    calendar = {}

    # Group by Day and Block
    for _, row in results_df.iterrows():
        day = row["Day"]
        block = row["Block"]

        if day not in calendar:
            calendar[day] = {}

        if block not in calendar[day]:
            calendar[day][block] = []

        # Add exam to this day/time slot
        calendar[day][block].append(
            {
                "CRN": str(row["CRN"]),
                "Course": row["Course"],
                "Room": row["Room"],
                "Capacity": int(row["Capacity"]),
                "Size": int(row["Size"]),
                "Valid": bool(row["Valid"]),
            }
        )

    return calendar
