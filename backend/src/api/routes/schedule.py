import io
import uuid
import zipfile

import numpy as np
import pandas as pd
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from src.algorithms.enhanced_dsatur_scheduler import export_student_schedule
from src.algorithms.original_dsatur_scheduler import (
    FriendDSATURExamGraph as OriginalDSATURExamGraph,
)
from src.schemas.db import Datasets, Users
from src.services.auth import get_current_user, get_session
from src.services.storage import storage_service


router = APIRouter(prefix="/schedule", tags=["Scheduling"])


def get_db():
    """Database session dependency"""
    db = get_session()
    try:
        yield db
    finally:
        db.close()


@router.post("/generate/{dataset_id}")
async def generate_schedule_from_dataset(
    dataset_id: str,
    max_per_day: int = Query(2, ge=1, le=5),
    avoid_back_to_back: bool = Query(True),
    max_days: int = Query(7, ge=1, le=7),
    current_user: Users = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generate schedule from a dataset by loading files from storage and running the original DSATUR algorithm."""

    try:
        # Look up the dataset
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

        # Load files from storage
        file_paths = {}
        for file_entry in dataset.file_paths:
            file_type = file_entry["type"]
            storage_key = file_entry["storage_key"]
            file_content = storage_service.download_file(storage_key)

            if file_content is None:
                raise HTTPException(
                    500, f"Failed to load {file_type} file from storage"
                )

            # Read into DataFrame
            df = pd.read_csv(io.BytesIO(file_content))

            # Map to expected column names for the scheduler
            if file_type == "courses":
                # Expected by scheduler: CRN, course_ref, num_students
                # Create course_ref from CourseID
                if "course_ref" not in df.columns and "CourseID" in df.columns:
                    df["course_ref"] = df["CourseID"].astype(str)
                elif "course_ref" not in df.columns:
                    df["course_ref"] = df["CRN"].astype(str)
                file_paths["census"] = df
            elif file_type == "enrollments":
                # Expected by scheduler: student_id, CRN, instructor_name
                # Rename Student_PIDM to student_id
                if "Student_PIDM" in df.columns:
                    df = df.rename(columns={"Student_PIDM": "student_id"})
                # Rename Instructor Name to instructor_name
                if "Instructor Name" in df.columns:
                    df = df.rename(columns={"Instructor Name": "instructor_name"})
                # Add instructor_name column if it doesn't exist (fill with empty string)
                if "instructor_name" not in df.columns:
                    df["instructor_name"] = ""
                file_paths["enrollment"] = df
            elif file_type == "rooms":
                # Expected: room_name, capacity
                file_paths["classrooms"] = df

        # Run the original DSATUR algorithm
        graph = OriginalDSATURExamGraph(
            file_paths["census"],
            file_paths["enrollment"],
            file_paths["classrooms"],
            weight_large_late=1,
            weight_b2b_student=6 if avoid_back_to_back else 0,
            weight_b2b_instructor=2 if avoid_back_to_back else 0,
        )

        graph.build_graph()
        graph.dsatur_color()
        graph.dsatur_schedule(max_days=max_days)
        results_df = graph.assign_rooms()

        # Get summary - convert to plain dict immediately
        summary_raw = graph.summary()
        print(f"Summary type: {type(summary_raw)}")
        print(f"Summary content: {summary_raw}")

        # Convert summary to plain dict with native types
        summary = {}
        if isinstance(summary_raw, dict):
            for key, value in summary_raw.items():
                summary[key] = (
                    int(value) if isinstance(value, (int, np.integer)) else value
                )
        else:
            raise ValueError(f"Summary is not a dict: {type(summary_raw)}")

        # Get failures - handle carefully
        try:
            failures_df = graph.fail_report()
            print(f"Failures type: {type(failures_df)}")

            if hasattr(failures_df, "empty") and not failures_df.empty:
                # Convert DataFrame to plain Python dicts
                failure_records = []
                for _idx, row in failures_df.iterrows():
                    failure_records.append(
                        {
                            "CRN": str(row.get("CRN", "")),
                            "Course": str(row.get("Course", "")),
                            "Size": int(row.get("Size", 0))
                            if pd.notna(row.get("Size"))
                            else 0,
                            "reasons": dict(row.get("reasons", {}))
                            if isinstance(row.get("reasons"), dict)
                            else {},
                        }
                    )
            else:
                failure_records = []
        except Exception as e:
            print(f"Error processing failures: {e}")
            failure_records = []

        # Convert results DataFrame to list of dicts with native types
        schedule_exams = []
        for _idx, row in results_df.iterrows():
            schedule_exams.append(
                {
                    "CRN": str(row["CRN"]),
                    "Course": str(row["Course"]),
                    "Day": str(row["Day"]),
                    "Block": str(row["Block"]),
                    "Room": str(row["Room"]),
                    "Capacity": int(row["Capacity"])
                    if pd.notna(row["Capacity"])
                    else 0,
                    "Size": int(row["Size"]) if pd.notna(row["Size"]) else 0,
                    "Valid": bool(row["Valid"]) if pd.notna(row["Valid"]) else False,
                }
            )

        # Create calendar data
        calendar_data = {}
        for exam in schedule_exams:
            day = exam["Day"]
            block = exam["Block"]

            if day not in calendar_data:
                calendar_data[day] = {}
            if block not in calendar_data[day]:
                calendar_data[day][block] = []

            calendar_data[day][block].append(
                {
                    "CRN": exam["CRN"],
                    "Course": exam["Course"],
                    "Room": exam["Room"],
                    "Capacity": exam["Capacity"],
                    "Size": exam["Size"],
                    "Valid": exam["Valid"],
                }
            )

        # Create conflicts data
        conflict_rows = []
        try:
            if (
                hasattr(graph, "student_soft_violations")
                and not graph.student_soft_violations.empty
            ):
                for _idx, row in graph.student_soft_violations.iterrows():
                    blocks = row.get("blocks", [])
                    if isinstance(blocks, (list, np.ndarray)):
                        blocks = [int(b) for b in blocks]
                    else:
                        blocks = []

                    conflict_rows.append(
                        {
                            "student_id": str(row["student_id"]),
                            "day": str(row["day"]),
                            "conflict_type": str(row["violation"]),
                            "blocks": blocks,
                        }
                    )
        except Exception as e:
            print(f"Error processing conflicts: {e}")
            conflict_rows = []

        response_data = {
            "dataset_id": dataset_id,
            "dataset_name": dataset.dataset_name,
            "summary": {
                "num_classes": summary.get("num_classes", 0),
                "num_students": summary.get("num_students", 0),
                "potential_overlaps": 0,
                "real_conflicts": summary.get("hard_student_conflicts", 0)
                + summary.get("hard_instructor_conflicts", 0),
                "num_rooms": summary.get("num_rooms", 0),
                "slots_used": summary.get("slots_used", 0),
            },
            "conflicts": {
                "total": len(conflict_rows),
                "breakdown": conflict_rows,
                "details": {},
            },
            "failures": failure_records,
            "schedule": {
                "complete": schedule_exams,
                "calendar": calendar_data,
                "total_exams": len(schedule_exams),
            },
            "parameters": {
                "max_per_day": max_per_day,
                "avoid_back_to_back": avoid_back_to_back,
                "max_days": max_days,
            },
        }

        return response_data

    except ValueError as e:
        raise HTTPException(400, f"Invalid dataset ID format: {str(e)}") from e
    except HTTPException:
        raise
    except Exception as e:
        import traceback

        print(f"Full error traceback: {traceback.format_exc()}")
        raise HTTPException(500, f"Schedule generation error: {str(e)}") from e


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
    graph = OriginalDSATURExamGraph(census_df, enrollment_df, classrooms_df)
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
    graph = OriginalDSATURExamGraph(census_df, enrollment_df, classrooms_df)
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
