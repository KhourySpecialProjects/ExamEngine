from collections import defaultdict
from typing import Any
from uuid import UUID

import pandas as pd

from src.algorithms.enhanced_dsatur_scheduler import DSATURExamGraph
from src.core.exceptions import (
    DatasetNotFoundError,
    ScheduleGenerationError,
    ValidationError,
)
from src.repo.conflict_analyses import ConflictAnalysesRepo
from src.repo.course import CourseRepo
from src.repo.exam_assignment import ExamAssignmentRepo
from src.repo.room import RoomRepo
from src.repo.run import RunRepo
from src.repo.schedule import ScheduleRepo
from src.repo.time_slot import TimeSlotRepo
from src.schemas.db import StatusEnum
from src.services.dataset import DatasetService


class ScheduleService:
    """
    Business logic for exam schedule generation and management.

    Orchestrates the complete schedule generation workflow:
    1. Load dataset files from S3
    2. Execute DSATUR algorithm
    3. Create database records for courses, rooms, time slots
    4. Create schedule and run records
    5. Save exam assignments
    6. Save conflicts
    7. Update run status
    """

    def __init__(
        self,
        schedule_repo: ScheduleRepo,
        run_repo: RunRepo,
        exam_assignment_repo: ExamAssignmentRepo,
        conflict_analyses_repo: ConflictAnalysesRepo,
        course_repo: CourseRepo,
        time_slot_repo: TimeSlotRepo,
        room_repo: RoomRepo,
        dataset_service: DatasetService,
    ):
        self.schedule_repo = schedule_repo
        self.run_repo = run_repo
        self.exam_assignment_repo = exam_assignment_repo
        self.conflict_analyses_repo = conflict_analyses_repo
        self.course_repo = course_repo
        self.time_slot_repo = time_slot_repo
        self.room_repo = room_repo
        self.dataset_service = dataset_service

    async def generate_schedule(
        self,
        dataset_id: UUID,
        user_id: UUID,
        schedule_name: str,
        student_max_per_day: int = 3,
        instructor_max_per_day: int = 3,
        avoid_back_to_back: bool = True,
        max_days: int = 7,
        prioritize_large_courses: bool = False,
    ) -> dict[str, Any]:
        """
        Generate complete exam schedule from dataset.

        This is the main orchestration method that coordinates:
        - Dataset loading
        - Algorithm execution
        - Database persistence
        - Error handling and rollback

        Args:
            dataset_id: Dataset to schedule
            user_id: User generating schedule
            schedule_name: Unique name for this schedule
            student_max_per_day: Max exams per student per day
            instructor_max_per_day: Max exams per instructor per day
            avoid_back_to_back: Avoid consecutive exam blocks
            max_days: Days to spread exams across
            prioritize_large_courses: If True, schedule largest courses first (default: False)

        Returns:
            Complete schedule with all metadata

        Raises:
            DatasetNotFoundError: If dataset doesn't exist
            ValidationError: If schedule_name already exists
            ScheduleGenerationError: If algorithm fails
        """
        if self.schedule_repo.name_exists(schedule_name, user_id):
            raise ValidationError(
                f"Schedule name '{schedule_name}' already exists",
                detail={"field": "schedule_name"},
            )

        # Create Run and Schedule records (status: Running)
        parameters = {
            "student_max_per_day": student_max_per_day,
            "instructor_max_per_day": instructor_max_per_day,
            "avoid_back_to_back": avoid_back_to_back,
            "max_days": max_days,
            "prioritize_large_courses": prioritize_large_courses,
        }

        schedule, run = self.schedule_repo.create_schedule_with_run(
            schedule_name=schedule_name,
            dataset_id=dataset_id,
            user_id=user_id,
            algorithm_name=(
                "DSATUR (Large-first)" if prioritize_large_courses else "DSATUR"
            ),
            parameters=parameters,
        )

        try:
            files = await self.dataset_service.get_dataset_files(dataset_id, user_id)

            course_mapping = await self._ensure_courses_exist(
                dataset_id, files["courses"], files["enrollments"]
            )
            room_mapping = await self._ensure_rooms_exist(dataset_id, files["rooms"])

            graph = DSATURExamGraph(
                files["courses"],
                files["enrollments"],
                files["rooms"],
                student_max_per_day=student_max_per_day,
                instructor_max_per_day=instructor_max_per_day,
            )
            graph.build_graph()

            graph.dsatur_color()

            graph.dsatur_schedule(
                max_days=max_days,
                prioritize_large_courses=prioritize_large_courses,
            )

            results_df = graph.assign_rooms()

            try:
                await self._save_exam_assignments(
                    schedule_id=schedule.schedule_id,
                    dataset_id=dataset_id,
                    results_df=results_df,
                    graph=graph,
                    course_mapping=course_mapping,
                    room_mapping=room_mapping,
                )
            except Exception as db_error:
                self.schedule_repo.db.rollback()
                raise ScheduleGenerationError(
                    f"Failed to save exam assignments: {str(db_error)}"
                ) from db_error

            try:
                conflicts_response = await self._save_and_format_conflicts(
                    schedule_id=schedule.schedule_id,
                    graph=graph,
                )
            except Exception as db_error:
                self.schedule_repo.db.rollback()
                raise ScheduleGenerationError(
                    f"Failed to save conflicts: {str(db_error)}"
                ) from db_error

            try:
                conflict_payload = graph.conflict_report()
            except Exception:
                conflict_payload = conflicts_response.get("conflicts", {})

            self.run_repo.update_status(run.run_id, StatusEnum.Completed)

            summary = graph.summary()

            # Get dataset info for response
            dataset_info = self.dataset_service.get_dataset_info(dataset_id, user_id)

            response = {
                "schedule_id": str(schedule.schedule_id),
                "schedule_name": schedule.schedule_name,
                "dataset_id": str(dataset_id),
                "dataset_name": dataset_info["dataset_name"],
                "summary": {
                    "num_classes": summary["num_classes"],
                    "num_students": summary["num_students"],
                    "potential_overlaps": 0,
                    "real_conflicts": conflicts_response["total_hard"],
                    "num_rooms": summary["num_rooms"],
                    "slots_used": summary["slots_used"],
                    "unplaced_exams": summary.get("unplaced_exams", 0),
                },
                # Provide the normalized conflict payload for the frontend
                "conflicts": conflict_payload,
                "failures": [],
                "schedule": {
                    "complete": results_df.to_dict(orient="records"),
                    "calendar": self._build_calendar_structure(results_df),
                    "total_exams": len(results_df),
                },
                "parameters": {
                    "student_max_per_day": student_max_per_day,
                    "instructor_max_per_day": instructor_max_per_day,
                    "avoid_back_to_back": avoid_back_to_back,
                    "max_days": max_days,
                    "prioritize_large_courses": prioritize_large_courses,
                },
            }

            return response

        except DatasetNotFoundError:
            self.run_repo.update_status(run.run_id, StatusEnum.Failed)
            raise
        except Exception as e:
            # Update run status to Failed
            self.schedule_repo.db.rollback()
            self.run_repo.update_status(run.run_id, StatusEnum.Failed)
            raise ScheduleGenerationError(
                f"Schedule generation failed: {str(e)}"
            ) from e

    def delete_schedule(self, schedule_id: UUID, user_id: UUID) -> dict[str, Any]:
        """
        Delete schedule and all related data.

        Cascades to exam assignments and conflicts.
        """
        success = self.schedule_repo.delete_schedule_cascade(schedule_id, user_id)

        if not success:
            raise DatasetNotFoundError(
                f"Schedule {schedule_id} not found or access denied"
            )

        return {"message": "Schedule deleted", "schedule_id": str(schedule_id)}

    def list_schedules_for_user(
        self,
        user_id: UUID,
    ) -> list[dict[str, Any]]:
        """
        List all schedules for user with metadata.

        Returns lightweight schedule info for list views.
        Includes information about whether schedule is owned or shared.
        """
        from src.repo.schedule_share import ScheduleShareRepo

        schedules = self.schedule_repo.get_all_for_user(user_id)
        share_repo = ScheduleShareRepo(self.schedule_repo.db)

        result = []
        for s in schedules:
            # Get counts
            exam_count = self.schedule_repo.get_exam_assignments_count(s.schedule_id)

            # Check if user owns this schedule
            is_owner = s.run.user_id == user_id

            # Get creator information
            created_by_user_id = str(s.run.user_id)
            created_by_user_name = s.run.user.name if s.run.user else "Unknown"

            # If not owner, get share information
            is_shared = False
            shared_by_user_id = None
            shared_by_user_name = None
            if not is_owner:
                share = share_repo.get_share_by_schedule_and_user(
                    s.schedule_id, user_id
                )
                if share and share.shared_by_user:
                    is_shared = True
                    shared_by_user_id = str(share.shared_by_user_id)
                    shared_by_user_name = share.shared_by_user.name

            result.append(
                {
                    "schedule_id": str(s.schedule_id),
                    "schedule_name": s.schedule_name,
                    "created_at": s.created_at.isoformat(),
                    "algorithm": s.run.algorithm_name,
                    "parameters": s.run.parameters,
                    "status": s.run.status.value,
                    "dataset_id": str(s.run.dataset_id),
                    "total_exams": exam_count,
                    "is_owner": is_owner,
                    "is_shared": is_shared,
                    "created_by_user_id": created_by_user_id,
                    "created_by_user_name": created_by_user_name,
                    "shared_by_user_id": shared_by_user_id,
                    "shared_by_user_name": shared_by_user_name,
                }
            )

        return result

    async def get_schedule_with_details(
        self, schedule_id: UUID, user_id: UUID
    ) -> dict[str, Any] | None:
        """
        Get complete schedule details including all exams and conflicts.

        This reconstructs the full ScheduleResult format that matches
        what the generate endpoint returns to make it consistent.
        """
        schedule = self.schedule_repo.get_with_run_details(schedule_id, user_id)
        if not schedule:
            return None

        exam_assignments = self.exam_assignment_repo.get_all_for_schedule(schedule_id)
        conflict_analysis = self.conflict_analyses_repo.get_by_schedule_id(schedule_id)

        calendar, complete_exams = self._build_schedule_data(exam_assignments)

        conflicts_data = self._build_conflicts_data(conflict_analysis)

        summary = self._calculate_summary_stats(
            exam_assignments, calendar, conflicts_data
        )

        # Check if user owns this schedule
        is_owner = schedule.run.user_id == user_id

        # Get creator information
        created_by_user_id = str(schedule.run.user_id)
        created_by_user_name = schedule.run.user.name if schedule.run.user else "Unknown"

        # If not owner, get share information
        is_shared = False
        shared_by_user_id = None
        shared_by_user_name = None
        if not is_owner:
            from src.repo.schedule_share import ScheduleShareRepo

            share_repo = ScheduleShareRepo(self.schedule_repo.db)
            share = share_repo.get_share_by_schedule_and_user(
                schedule_id, user_id
            )
            if share and share.shared_by_user:
                is_shared = True
                shared_by_user_id = str(share.shared_by_user_id)
                shared_by_user_name = share.shared_by_user.name

        return {
            "schedule_id": str(schedule.schedule_id),
            "schedule_name": schedule.schedule_name,
            "created_at": schedule.created_at.isoformat(),
            "dataset_id": str(schedule.run.dataset.dataset_id),
            "dataset_name": schedule.run.dataset.dataset_name,
            "summary": summary,
            "conflicts": conflicts_data,
            "failures": [],
            "schedule": {
                "complete": complete_exams,
                "calendar": calendar,
                "total_exams": len(exam_assignments),
            },
            "parameters": schedule.run.parameters,
            "algorithm": schedule.run.algorithm_name,
            "status": schedule.run.status.value,
            "is_owner": is_owner,
            "is_shared": is_shared,
            "created_by_user_id": created_by_user_id,
            "created_by_user_name": created_by_user_name,
            "shared_by_user_id": shared_by_user_id,
            "shared_by_user_name": shared_by_user_name,
        }

    def _build_schedule_data(
        self, exam_assignments: list
    ) -> tuple[dict[str, dict[str, list[dict]]], list[dict]]:
        """
        Build calendar and complete exam list from assignments.

        Returns:
            Tuple of (calendar_dict, complete_exams_list)
        """
        calendar = defaultdict(lambda: defaultdict(list))
        complete_exams = []

        for assignment in exam_assignments:
            exam_data = self._assignment_to_exam_dict(assignment)

            # Add to complete list
            complete_exams.append(exam_data)

            # Add to calendar
            day = assignment.time_slot.day.value
            slot_label = assignment.time_slot.slot_label
            calendar[day][slot_label].append(self._exam_dict_for_calendar(assignment))

        return dict(calendar), complete_exams

    def _assignment_to_exam_dict(self, assignment) -> dict[str, Any]:
        """Convert exam assignment to complete exam record format."""
        return {
            "CRN": assignment.course.crn,
            "Course": assignment.course.course_subject_code,
            "Day": assignment.time_slot.day.value,
            "Block": assignment.time_slot.slot_label,
            "Room": assignment.room.location,
            "Capacity": assignment.room.capacity,
            "Size": assignment.course.enrollment_count,
            "Valid": True,
            "Instructor": assignment.course.instructor_name,
        }

    def _exam_dict_for_calendar(self, assignment) -> dict[str, Any]:
        """Convert exam assignment to calendar entry format (subset of fields)."""
        return {
            "CRN": assignment.course.crn,
            "Course": assignment.course.course_subject_code,
            "Room": assignment.room.location,
            "Capacity": assignment.room.capacity,
            "Size": assignment.course.enrollment_count,
            "Valid": True,
            "Instructor": assignment.course.instructor_name,
        }

    def _build_conflicts_data(self, conflict_analysis) -> dict[str, Any]:
        """
        Extract and format conflicts from conflict analysis.

        Returns:
            Dictionary with total count, breakdown list, and details
        """
        if not conflict_analysis or not conflict_analysis.conflicts:
            return {"total": 0, "breakdown": [], "details": {}}

        conflicts_json = conflict_analysis.conflicts
        hard_conflicts = conflicts_json.get("hard_conflicts", {})
        soft_conflicts = conflicts_json.get("soft_conflicts", {})

        # Block to time mapping
        block_time_map = {
            0: "9AM-11AM",
            1: "11:30AM-1:30PM",
            2: "2PM-4PM",
            3: "4:30PM-6:30PM",
            4: "7PM-9PM",
        }

        # Get course names from database for this schedule
        schedule_id = conflict_analysis.schedule_id
        exam_assignments = self.exam_assignment_repo.get_all_for_schedule(schedule_id)
        course_name_map = {}
        for assignment in exam_assignments:
            crn = assignment.course.crn
            course_name = assignment.course.course_subject_code
            course_name_map[str(crn)] = course_name

        # Enrich conflicts with block_time and course names if missing
        def enrich_conflict(conflict: dict) -> dict:
            enriched = conflict.copy()
            # Add block_time if missing
            if "block_time" not in enriched and "block" in enriched:
                enriched["block_time"] = block_time_map.get(enriched["block"], "")
            # Add course name if missing
            if "course" not in enriched or enriched.get("course") == "Unknown":
                crn = enriched.get("crn")
                if crn:
                    enriched["course"] = course_name_map.get(str(crn), "Unknown")
            # Add conflicting course names if missing
            if "conflicting_crn" in enriched and "conflicting_course" not in enriched:
                conflicting_crn = enriched.get("conflicting_crn")
                if conflicting_crn:
                    enriched["conflicting_course"] = course_name_map.get(str(conflicting_crn), "Unknown")
            if "conflicting_crns" in enriched and "conflicting_courses" not in enriched:
                conflicting_crns = enriched.get("conflicting_crns", [])
                enriched["conflicting_courses"] = [
                    course_name_map.get(str(crn), "Unknown") for crn in conflicting_crns
                ]
            return enriched

        # Enrich all conflicts
        for conflict_type, conflicts_list in hard_conflicts.items():
            hard_conflicts[conflict_type] = [enrich_conflict(c) for c in conflicts_list]

        breakdown = []

        # Process hard conflicts
        breakdown.extend(
            self._process_double_book_conflicts(
                hard_conflicts.get("student_double_book", []),
                "student_double_book",
                entity_key="student_id",
            )
        )

        breakdown.extend(
            self._process_double_book_conflicts(
                hard_conflicts.get("instructor_double_book", []),
                "instructor_double_book",
                entity_key="entity_id",
            )
        )

        breakdown.extend(
            self._process_max_per_day_conflicts(
                hard_conflicts.get("student_gt_max_per_day", []),
                "student_gt_max_per_day",
                entity_key="student_id",
            )
        )

        breakdown.extend(
            self._process_max_per_day_conflicts(
                hard_conflicts.get("instructor_gt_max_per_day", []),
                "instructor_gt_max_per_day",
                entity_key="entity_id",
            )
        )

        # Process soft conflicts
        breakdown.extend(
            self._process_back_to_back_conflicts(
                soft_conflicts.get("back_to_back_students", []),
                "back_to_back",
                entity_key="student_id",
            )
        )

        breakdown.extend(
            self._process_back_to_back_conflicts(
                soft_conflicts.get("back_to_back_instructors", []),
                "back_to_back_instructor",
                entity_key="entity_id",
            )
        )

        statistics = conflicts_json.get("statistics", {})
        total_conflicts = statistics.get("total_hard_conflicts", 0)

        return {
            "total": total_conflicts,
            "breakdown": breakdown,
            "details": {},
        }

    def _process_double_book_conflicts(
        self, conflicts: list[dict], conflict_type: str, entity_key: str
    ) -> list[dict]:
        """Process double-booking conflicts (student or instructor)."""
        result = []
        for conflict in conflicts:
            record = {
                entity_key: conflict.get("entity_id"),
                "day": conflict.get("day"),
                "block": conflict.get("block"),
                "block_time": conflict.get("block_time"),
                "conflict_type": conflict_type,
                "crn": conflict.get("crn"),
                "course": conflict.get("course", "Unknown"),
                "conflicting_crn": conflict.get("conflicting_crn"),
                "conflicting_course": conflict.get("conflicting_course"),
            }
            # Handle conflicting_crns array if present
            if conflict.get("conflicting_crns"):
                record["conflicting_crns"] = conflict.get("conflicting_crns")
            if conflict.get("conflicting_courses"):
                record["conflicting_courses"] = conflict.get("conflicting_courses")
            result.append(record)
        return result

    def _process_max_per_day_conflicts(
        self, conflicts: list[dict], conflict_type: str, entity_key: str
    ) -> list[dict]:
        """Process max-per-day violations (student or instructor)."""
        result = []
        for conflict in conflicts:
            # For max_per_day conflicts, we need to get block_time for each CRN
            # But since these conflicts span multiple blocks, we'll use the day only
            record = {
                entity_key: conflict.get("entity_id"),
                "day": conflict.get("day"),
                "conflict_type": conflict_type,
                "crns": conflict.get("crns", []),
                "courses": conflict.get("courses", []),
            }
            result.append(record)
        return result

    def _process_back_to_back_conflicts(
        self, conflicts: list[dict], conflict_type: str, entity_key: str
    ) -> list[dict]:
        """Process back-to-back exam conflicts (student or instructor)."""
        return [
            {
                entity_key: conflict.get(entity_key),
                "day": conflict.get("day"),
                "blocks": conflict.get("blocks"),
                "conflict_type": conflict_type,
            }
            for conflict in conflicts
        ]

    def _calculate_summary_stats(
        self, exam_assignments: list, calendar: dict, conflicts_data: dict
    ) -> dict[str, int]:
        """Calculate summary statistics for the schedule."""
        unique_courses = {assignment.course for assignment in exam_assignments}
        unique_rooms = {assignment.room_id for assignment in exam_assignments}
        slots_used = len({(day, slot) for day in calendar for slot in calendar[day]})

        return {
            "num_classes": len(exam_assignments),
            "num_students": sum(course.enrollment_count for course in unique_courses),
            "potential_overlaps": 0,
            "real_conflicts": conflicts_data["total"],
            "num_rooms": len(unique_rooms),
            "slots_used": slots_used,
        }

    async def _ensure_courses_exist(
        self,
        dataset_id: UUID,
        courses_df: pd.DataFrame,
        enrollment_df: pd.DataFrame,
    ) -> dict[str, UUID]:
        """
        Ensure all courses exist in database.

        Creates course records if they don't exist.
        Returns mapping of course_ref -> course_id.
        """
        # Check if courses already exist for this dataset
        existing_courses = self.course_repo.get_all_for_dataset(dataset_id)

        if existing_courses:
            # Build mapping from existing records
            mapping = {course.crn: course.course_id for course in existing_courses}

            return mapping

        mapping = self.course_repo.bulk_create_from_dataframe(
            dataset_id, courses_df, enrollment_df=enrollment_df
        )
        return mapping

    async def _ensure_rooms_exist(
        self, dataset_id: UUID, rooms_df: pd.DataFrame
    ) -> dict[str, UUID]:
        """
        Ensure all rooms exist in database.

        Returns mapping of room_name -> room_id.
        """
        existing_rooms = self.room_repo.get_all_for_dataset(dataset_id)

        if existing_rooms:
            mapping = {room.location: room.room_id for room in existing_rooms}
            return mapping

        return self.room_repo.bulk_create_from_dataframe(dataset_id, rooms_df)

    async def _save_exam_assignments(
        self,
        schedule_id: UUID,
        dataset_id: UUID,
        results_df: pd.DataFrame,
        graph: DSATURExamGraph,
        course_mapping: dict[str, UUID],
        room_mapping: dict[str, UUID],
    ) -> None:
        """
        Save exam assignments to database.

        Converts DSATUR results (DataFrame with CRN, Day, Block, Room)
        into ExamAssignment records with proper foreign keys.
        """
        assignments = []

        for _, row in results_df.iterrows():
            crn = row["CRN"]
            room_name = row["Room"]

            # Get course_id from mapping
            course_id = course_mapping.get(crn)
            if not course_id:
                # Skip courses not found (shouldn't happen)
                continue

            # Get room_id from mapping
            room_id = room_mapping.get(room_name)
            if not room_id:
                continue

            # Get day and block from graph assignment
            if crn not in graph.assignment:
                continue

            day_idx, block_idx = graph.assignment[crn]
            day_name = graph.day_names[day_idx]

            # Get or create time slot
            time_slot = self.time_slot_repo.get_or_create_slot(
                dataset_id=dataset_id, day=day_name, block_index=block_idx
            )

            assignments.append(
                {
                    "course_id": course_id,
                    "time_slot_id": time_slot.time_slot_id,
                    "room_id": room_id,
                }
            )

        # Bulk create all assignments
        if assignments:
            self.exam_assignment_repo.bulk_create(schedule_id, assignments)

    async def _save_and_format_conflicts(
        self,
        schedule_id: UUID,
        graph: DSATURExamGraph,
    ) -> dict:
        """
        Save conflicts to database and return formatted response.

        Returns dict with structure:
        {
            "total_hard": int,
            "total_soft": int,
            "conflicts": {
                "total": int,
                "breakdown": [...],
                "details": {}
            }
        }
        """
        # Build hard conflicts structure
        hard_conflicts = {
            "student_double_book": [],
            "student_gt_max_per_day": [],
            "instructor_double_book": [],
            "instructor_gt_max_per_day": [],
        }

        # Block to time mapping
        block_time_map = {
            0: "9AM-11AM",
            1: "11:30AM-1:30PM",
            2: "2PM-4PM",
            3: "4:30PM-6:30PM",
            4: "7PM-9PM",
        }

        # Get course names from census data
        course_name_map = {}
        if hasattr(graph, "census") and not graph.census.empty:
            # Try different column name variations
            crn_col = None
            course_col = None
            for col in graph.census.columns:
                if col.upper() in ["CRN", "COURSE_REF", "COURSEID"]:
                    crn_col = col
                if col.upper() in ["COURSE", "COURSE_REF", "COURSEID", "COURSE_SUBJECT_CODE"]:
                    course_col = col
            
            if crn_col and course_col:
                for _, row in graph.census.iterrows():
                    crn_val = str(row[crn_col])
                    course_val = str(row[course_col])
                    course_name_map[crn_val] = course_val

        # Process graph.conflicts list
        for conflict_tuple in graph.conflicts:
            if len(conflict_tuple) == 5:
                conflict_type, entity_id, day, block, crn = conflict_tuple
                conflicting_info = None
            else:
                conflict_type, entity_id, day, block, crn, conflicting_info = (
                    conflict_tuple
                )

            # Get course name
            crn_str = str(crn)
            course_name = course_name_map.get(crn_str, "Unknown")

            conflict_record = {
                "entity_id": entity_id,
                "day": graph.day_names[day] if day < len(graph.day_names) else str(day),
                "block": block,
                "block_time": block_time_map.get(block, f"Block {block}"),
                "crn": crn_str,
                "course": course_name,
            }

            if conflicting_info:
                if isinstance(conflicting_info, list):
                    conflict_record["conflicting_crns"] = conflicting_info
                    # Try to get course names for conflicting CRNs
                    conflicting_courses = [
                        course_name_map.get(str(c), "Unknown") for c in conflicting_info
                    ]
                    if conflicting_courses:
                        conflict_record["conflicting_courses"] = conflicting_courses
                else:
                    conflict_record["conflicting_crn"] = str(conflicting_info)
                    conflicting_course = course_name_map.get(str(conflicting_info), "Unknown")
                    if conflicting_course != "Unknown":
                        conflict_record["conflicting_course"] = conflicting_course

            if conflict_type in hard_conflicts:
                hard_conflicts[conflict_type].append(conflict_record)

        # Build soft conflicts structure
        soft_conflicts = {
            "back_to_back_students": [],
            "back_to_back_instructors": [],
            "large_courses_not_early": [],
        }

        # Process student back-to-back
        if not graph.student_soft_violations.empty:
            for _, row in graph.student_soft_violations.iterrows():
                soft_conflicts["back_to_back_students"].append(
                    {
                        "student_id": str(row["student_id"]),
                        "day": row["day"],
                        "blocks": row["blocks"].tolist()
                        if hasattr(row["blocks"], "tolist")
                        else row["blocks"],
                    }
                )

        # Process instructor back-to-back
        if not graph.instructor_soft_violations.empty:
            for _, row in graph.instructor_soft_violations.iterrows():
                soft_conflicts["back_to_back_instructors"].append(
                    {
                        "instructor_name": row["instructor_name"],
                        "day": row["day"],
                        "blocks": row["blocks"].tolist()
                        if hasattr(row["blocks"], "tolist")
                        else row["blocks"],
                    }
                )

        # Process large courses not early
        if not graph.large_courses_not_early.empty:
            for _, row in graph.large_courses_not_early.iterrows():
                soft_conflicts["large_courses_not_early"].append(
                    {
                        "crn": row["CRN"],
                        "course": row["Course"],
                        "size": int(row["Size"]),
                        "day": row["Day"],
                    }
                )

        # Get statistics from algorithm
        summary = graph.summary()
        total_hard = (
            summary.get("student_double_book", 0)
            + summary.get("student_gt_max_per_day", 0)
            + summary.get("instructor_double_book", 0)
            + summary.get("instructor_gt_max_per_day", 0)
        )
        total_soft = (
            summary.get("students_back_to_back", 0)
            + summary.get("instructors_back_to_back", 0)
            + summary.get("large_courses_not_early", 0)
        )

        # Build complete data structure
        conflicts_data = {
            "hard_conflicts": hard_conflicts,
            "soft_conflicts": soft_conflicts,
            "statistics": {
                "student_double_book_count": summary.get("student_double_book", 0),
                "student_gt_max_per_day_count": summary.get(
                    "student_gt_max_per_day", 0
                ),
                "instructor_double_book_count": summary.get(
                    "instructor_double_book", 0
                ),
                "instructor_gt_max_per_day_count": summary.get(
                    "instructor_gt_max_per_day", 0
                ),
                "back_to_back_students_count": summary.get("students_back_to_back", 0),
                "back_to_back_instructors_count": summary.get(
                    "instructors_back_to_back", 0
                ),
                "large_courses_not_early_count": summary.get(
                    "large_courses_not_early", 0
                ),
                "total_hard_conflicts": total_hard,
                "total_soft_conflicts": total_soft,
            },
        }

        # Save to database
        self.conflict_analyses_repo.create_analysis(
            schedule_id=schedule_id,
            conflicts_data=conflicts_data,
        )

        # Format breakdown for frontend
        breakdown = []

        # Add hard conflicts
        for conflict_type in [
            "student_double_book",
            "instructor_double_book",
            "student_gt_max_per_day",
            "instructor_gt_max_per_day",
        ]:
            for conflict in hard_conflicts[conflict_type]:
                breakdown.append(
                    {
                        "conflict_type": conflict_type,
                        "entity_id": conflict["entity_id"],
                        "day": conflict["day"],
                        "block": conflict.get("block"),
                        "crn": conflict.get("crn"),
                        "conflicting_crn": conflict.get("conflicting_crn"),
                        "conflicting_crns": conflict.get("conflicting_crns", []),
                    }
                )

        # Add soft conflicts
        for student_c in soft_conflicts["back_to_back_students"]:
            breakdown.append(
                {
                    "conflict_type": "back_to_back_student",
                    "student_id": student_c["student_id"],
                    "entity_id": student_c["student_id"],
                    "day": student_c["day"],
                    "blocks": student_c["blocks"],
                }
            )

        for instr_c in soft_conflicts["back_to_back_instructors"]:
            breakdown.append(
                {
                    "conflict_type": "back_to_back_instructor",
                    "entity_id": instr_c["instructor_name"],
                    "day": instr_c["day"],
                    "blocks": instr_c["blocks"],
                }
            )

        for course_c in soft_conflicts["large_courses_not_early"]:
            breakdown.append(
                {
                    "conflict_type": "large_course_not_early",
                    "entity_id": course_c["crn"],
                    "crn": course_c["crn"],
                    "course": course_c["course"],
                    "size": course_c["size"],
                    "day": course_c["day"],
                }
            )

        return {
            "total_hard": total_hard,
            "total_soft": total_soft,
            "conflicts": {
                "total": total_hard + total_soft,
                "breakdown": breakdown,
                "details": {},
            },
        }

    def _build_calendar_structure(self, results_df: pd.DataFrame) -> dict:
        """
        Convert DataFrame to nested calendar structure.

        Returns:
            {
                "Monday": {
                    "9AM-11AM": [exam1, exam2, ...],
                    "11:30AM-1:30PM": [...]
                },
                "Tuesday": {...}
            }
        """
        calendar = {}

        for _, row in results_df.iterrows():
            day = row["Day"]
            block = row["Block"]

            if day not in calendar:
                calendar[day] = {}
            if block not in calendar[day]:
                calendar[day][block] = []

            calendar[day][block].append(
                {
                    "CRN": str(row["CRN"]),
                    "Course": row["Course"],
                    "Room": row["Room"],
                    "Capacity": int(row["Capacity"]),
                    "Size": int(row["Size"]),
                    "Valid": bool(row["Valid"]),
                    "Instructor": row["Instructor"],
                }
            )

        return calendar
