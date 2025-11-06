import io
import json
import re
import uuid
import zipfile

import numpy as np
import pandas as pd
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.orm import Session

from src.algorithms.enhanced_dsatur_scheduler import (
    DSATURExamGraph,
    export_student_schedule,
)
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
    instructor_per_day: int = Query(2, ge=1, le=5),
    avoid_back_to_back: bool = Query(True),
    max_days: int = Query(7, ge=1, le=7),
    current_user: Users = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generate schedule from a dataset by loading files from storage and running the enhanced DSATUR algorithm."""

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
            
            # Check if file exists first
            if not storage_service.file_exists(storage_key):
                raise HTTPException(
                    500, 
                    f"Failed to load {file_type} file from storage: File not found (key: {storage_key}). "
                    f"This may indicate the file was deleted or the storage key is incorrect."
                )
            
            file_content = storage_service.download_file(storage_key)

            if file_content is None:
                raise HTTPException(
                    500, 
                    f"Failed to load {file_type} file from storage (key: {storage_key}). "
                    f"Check backend logs for detailed error information. "
                    f"This may be due to AWS credentials, network issues, or storage permissions."
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

        # Run the enhanced DSATUR algorithm with instructor support
        graph = DSATURExamGraph(
            file_paths["census"],
            file_paths["enrollment"],
            file_paths["classrooms"],
            weight_large_late=1,
            weight_b2b_student=6 if avoid_back_to_back else 0,
            weight_b2b_instructor=2 if avoid_back_to_back else 0,
            max_student_per_day=max_per_day,
            max_instructor_per_day=instructor_per_day,
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
                    # Extract Course - handle both scalar and Series cases
                    course_value = row.get("Course", "")
                    if isinstance(course_value, pd.Series):
                        course_str = str(course_value.iloc[0]) if len(course_value) > 0 else ""
                    else:
                        course_str = str(course_value) if course_value is not None and not pd.isna(course_value) else ""
                    
                    failure_records.append(
                        {
                            "CRN": str(row.get("CRN", "")),
                            "Course": course_str,
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
            # Extract Course - handle both scalar and Series cases
            course_value = row["Course"]
            if isinstance(course_value, pd.Series):
                # If it's a Series, get the first value
                course_str = str(course_value.iloc[0]) if len(course_value) > 0 else ""
            elif isinstance(course_value, str):
                # If it's already a string, check if it looks like a Series string representation
                # Pattern: "course_ref COMM1101 course_ref COMM1101 Name: 580, dtype: object"
                if "dtype:" in course_value and "Name:" in course_value:
                    # Extract the actual course code (e.g., "COMM1101")
                    # Try to find a pattern like "course_ref CODE" or just extract the code
                    # Look for patterns like "COMM1101", "SOCL1102", etc. (4 letters + 4 digits)
                    match = re.search(r'([A-Z]{4}\d{4})', course_value)
                    if match:
                        course_str = match.group(1)
                    else:
                        # Fallback: try to get the value after "course_ref"
                        parts = course_value.split()
                        if "course_ref" in parts:
                            idx = parts.index("course_ref")
                            if idx + 1 < len(parts):
                                course_str = parts[idx + 1]
                            else:
                                course_str = course_value
                        else:
                            course_str = course_value
                else:
                    course_str = course_value
            else:
                # Normal case: scalar value (int, float, etc.)
                course_str = str(course_value) if course_value is not None and not pd.isna(course_value) else ""
            
            # Get instructor name(s) for this CRN
            crn = str(row["CRN"])
            instructor_set = graph.instructors_by_crn.get(crn, set())
            # Join multiple instructors with comma, or use "TBD" if none
            if instructor_set:
                instructor_name = ", ".join(sorted(str(i) for i in instructor_set if i and str(i).strip()))
            else:
                instructor_name = "TBD"
            
            schedule_exams.append(
                {
                    "CRN": crn,
                    "Course": course_str,
                    "Day": str(row["Day"]),
                    "Block": str(row["Block"]),
                    "Room": str(row["Room"]),
                    "Capacity": int(row["Capacity"])
                    if pd.notna(row["Capacity"])
                    else 0,
                    "Size": int(row["Size"]) if pd.notna(row["Size"]) else 0,
                    "Valid": bool(row["Valid"]) if pd.notna(row["Valid"]) else False,
                    "Instructor": instructor_name,
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
                    "Instructor": exam.get("Instructor", "TBD"),
                }
            )

        # Create conflicts data - include both hard conflicts and soft violations
        conflict_rows = []
        try:
            # Add hard conflicts from the tracked conflict list
            if hasattr(graph, "conflicts") and graph.conflicts:
                # Debug: print conflict count
                print(f"Total conflicts in graph.conflicts: {len(graph.conflicts)}")
                for conflict_tuple in graph.conflicts:
                    try:
                        # Debug: print conflict tuple format
                        print(f"Processing conflict tuple: {conflict_tuple}, length: {len(conflict_tuple)}")
                        
                        # Handle both old format (5 elements) and new format (6 elements)
                        if len(conflict_tuple) == 5:
                            conflict_type, entity_id, day, block, crn = conflict_tuple
                            conflicting_crn = None
                            conflicting_crns = []
                        elif len(conflict_tuple) >= 6:
                            conflict_type, entity_id, day, block, crn, conflicting_info = conflict_tuple[:6]
                            print(f"  Conflict type: {conflict_type}, entity: {entity_id}, day: {day}, block: {block}, crn: {crn}")
                            print(f"  Conflicting info: {conflicting_info}, type: {type(conflicting_info)}")
                            
                            # conflicting_info can be a single CRN (string) or a list of CRNs, or None
                            if conflicting_info is None:
                                conflicting_crn = None
                                conflicting_crns = []
                            elif isinstance(conflicting_info, list):
                                conflicting_crns = [str(c) for c in conflicting_info if c is not None]
                                conflicting_crn = conflicting_crns[0] if conflicting_crns else None
                            else:
                                conflicting_crn = str(conflicting_info) if conflicting_info else None
                                conflicting_crns = [conflicting_crn] if conflicting_crn else []
                        else:
                            print(f"Warning: Unexpected conflict tuple format: {conflict_tuple}")
                            continue
                    
                        # Get day name and block time
                        # day_names is a list, not a dict, so use indexing
                        if isinstance(day, int) and 0 <= day < len(graph.day_names):
                            day_name = graph.day_names[day]
                        else:
                            day_name = f"Day {day}"
                        
                        # block_times is a dict - ensure we get a string value
                        block_time_raw = graph.block_times.get(block, f"Block {block}")
                        block_time = str(block_time_raw) if block_time_raw is not None else f"Block {block}"
                        
                        # Ensure block is JSON-serializable (int or string)
                        if not isinstance(block, (int, str)):
                            block = int(block) if block is not None else 0
                        
                        # Get course names for CRNs - handle missing nodes gracefully and ensure JSON-serializable
                        # Convert NetworkX NodeView to dict to avoid serialization issues
                        try:
                            if crn in graph.G.nodes:
                                node_data = dict(graph.G.nodes[crn])  # Convert NodeView to dict
                                crn_course = str(node_data.get("course_ref", crn)) if node_data.get("course_ref") is not None else str(crn)
                            else:
                                crn_course = str(crn)
                        except Exception as e:
                            print(f"  Warning: Could not get course for CRN {crn}: {e}")
                            crn_course = str(crn)
                        
                        conflicting_course = None
                        conflicting_courses = []
                        if conflicting_crn:
                            try:
                                if conflicting_crn in graph.G.nodes:
                                    node_data = dict(graph.G.nodes[conflicting_crn])  # Convert NodeView to dict
                                    conflicting_course = str(node_data.get("course_ref", conflicting_crn)) if node_data.get("course_ref") is not None else str(conflicting_crn)
                                else:
                                    conflicting_course = str(conflicting_crn)
                            except Exception as e:
                                print(f"  Warning: Could not get course for conflicting CRN {conflicting_crn}: {e}")
                                conflicting_course = str(conflicting_crn)
                        if conflicting_crns:
                            conflicting_courses = []
                            for c in conflicting_crns:
                                try:
                                    if c in graph.G.nodes:
                                        node_data = dict(graph.G.nodes[c])  # Convert NodeView to dict
                                        course_name = str(node_data.get("course_ref", c)) if node_data.get("course_ref") is not None else str(c)
                                    else:
                                        course_name = str(c)
                                    conflicting_courses.append(course_name)
                                except Exception as e:
                                    print(f"  Warning: Could not get course for conflicting CRN {c}: {e}")
                                    conflicting_courses.append(str(c))
                        
                        conflict_rows.append(
                            {
                                "entity_id": str(entity_id) if entity_id is not None else "",
                                "day": str(day_name) if day_name is not None else "",
                                "block": int(block) if isinstance(block, (int, float)) else str(block) if block is not None else "",
                                "block_time": str(block_time) if block_time is not None else "",
                                "crn": str(crn) if crn is not None else "",
                                "course": str(crn_course) if crn_course is not None else "",
                                "conflicting_crn": str(conflicting_crn) if conflicting_crn is not None else None,
                                "conflicting_course": str(conflicting_course) if conflicting_course is not None else None,
                                "conflicting_crns": [str(c) for c in conflicting_crns] if conflicting_crns else [],
                                "conflicting_courses": [str(c) for c in conflicting_courses] if conflicting_courses else [],
                                "conflict_type": str(conflict_type) if conflict_type is not None else "",
                            }
                        )
                    except Exception as e:
                        print(f"Error processing individual conflict tuple {conflict_tuple}: {e}")
                        import traceback
                        print(traceback.format_exc())
                        continue
            
            # Add soft violations (back-to-back warnings)
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
            import traceback
            print(f"Error processing conflicts: {e}")
            print(f"Traceback: {traceback.format_exc()}")
            conflict_rows = []
        
        # Debug: print final conflict count
        print(f"Total conflict_rows after processing: {len(conflict_rows)}")
        print(f"Hard conflicts from summary: {summary.get('hard_student_conflicts', 0) + summary.get('hard_instructor_conflicts', 0)}")
        
        # Debug: print sample conflict if any
        if graph.conflicts and len(conflict_rows) == 0:
            print(f"WARNING: Found {len(graph.conflicts)} conflicts in graph but 0 in conflict_rows!")
            print(f"Sample conflict tuple: {graph.conflicts[0] if graph.conflicts else 'None'}")
            print(f"Sample conflict type: {type(graph.conflicts[0]) if graph.conflicts else 'None'}")
            print(f"Sample conflict length: {len(graph.conflicts[0]) if graph.conflicts else 'None'}")

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

        # Always clean response data to ensure JSON serializability
        # Clean first with our custom function, then use FastAPI's encoder
        try:
            response_data = _clean_for_json(response_data)
            # Try to serialize with json to catch any remaining issues
            json.dumps(response_data)
            return JSONResponse(content=response_data)
        except (TypeError, ValueError) as json_error:
            print(f"JSON serialization error after cleaning: {json_error}")
            print(f"Attempting with FastAPI's jsonable_encoder...")
            try:
                response_data = jsonable_encoder(response_data)
                return JSONResponse(content=response_data)
            except Exception as encoder_error:
                print(f"FastAPI encoder also failed: {encoder_error}")
                # Last resort: return a simplified error response
                return JSONResponse(
                    status_code=500,
                    content={
                        "error": "Failed to serialize response data",
                        "message": "The schedule was generated but could not be serialized. Check backend logs for details."
                    }
                )

    except ValueError as e:
        raise HTTPException(400, f"Invalid dataset ID format: {str(e)}") from e
    except HTTPException:
        raise
    except Exception as e:
        import traceback

        print(f"Full error traceback: {traceback.format_exc()}")
        raise HTTPException(500, f"Schedule generation error: {str(e)}") from e


def _clean_for_json(obj):
    """Recursively clean data structure to ensure JSON serializability"""
    # Handle None
    if obj is None:
        return None
    
    # Handle basic types
    if isinstance(obj, (bool, int, float, str)):
        return obj
    
    # Handle numpy types
    if isinstance(obj, (np.integer, np.int64, np.int32, np.int8, np.int16)):
        return int(obj)
    if isinstance(obj, (np.floating, np.float64, np.float32, np.float16)):
        return float(obj)
    if isinstance(obj, np.bool_):
        return bool(obj)
    if isinstance(obj, np.ndarray):
        return [_clean_for_json(item) for item in obj.tolist()]
    
    # Handle pandas types
    if isinstance(obj, pd.Series):
        return _clean_for_json(obj.to_dict())
    if isinstance(obj, pd.DataFrame):
        return _clean_for_json(obj.to_dict(orient="records"))
    
    # Handle dict-like objects (including NetworkX node dicts)
    if isinstance(obj, dict):
        try:
            return {str(k): _clean_for_json(v) for k, v in obj.items()}
        except (TypeError, AttributeError):
            # If it's not a real dict, try to convert
            try:
                return {str(k): _clean_for_json(v) for k, v in list(obj.items())}
            except Exception:
                return str(obj)
    
    # Handle list-like objects
    if isinstance(obj, (list, tuple)):
        return [_clean_for_json(item) for item in obj]
    
    # Handle sets
    if isinstance(obj, set):
        return [_clean_for_json(item) for item in list(obj)]
    
    # For everything else, try to convert to string
    try:
        # If it has __dict__, try to convert that
        if hasattr(obj, '__dict__'):
            return _clean_for_json(obj.__dict__)
        # Otherwise, just stringify
        return str(obj)
    except Exception:
        return None


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
