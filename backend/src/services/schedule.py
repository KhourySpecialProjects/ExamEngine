from typing import Any
from uuid import UUID

import pandas as pd

from src.algorithms.enhanced_dsatur_scheduler import DSATURExamGraph
from src.core.exceptions import (
    DatasetNotFoundError,
    ScheduleGenerationError,
    ValidationError,
)
from src.repo.conflict import ConflictRepo
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
        conflict_repo: ConflictRepo,
        course_repo: CourseRepo,
        time_slot_repo: TimeSlotRepo,
        room_repo: RoomRepo,
        dataset_service: DatasetService,
    ):
        self.schedule_repo = schedule_repo
        self.run_repo = run_repo
        self.exam_assignment_repo = exam_assignment_repo
        self.conflict_repo = conflict_repo
        self.course_repo = course_repo
        self.time_slot_repo = time_slot_repo
        self.room_repo = room_repo
        self.dataset_service = dataset_service

    async def generate_schedule(
        self,
        dataset_id: UUID,
        user_id: UUID,
        schedule_name: str,
        max_per_day: int = 3,
        avoid_back_to_back: bool = True,
        max_days: int = 7,
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
            max_per_day: Max exams per student per day
            avoid_back_to_back: Avoid consecutive exam blocks
            max_days: Days to spread exams across

        Returns:
            Complete schedule with all metadata

        Raises:
            DatasetNotFoundError: If dataset doesn't exist
            ValidationError: If schedule_name already exists
            ScheduleGenerationError: If algorithm fails
        """
        if self.schedule_repo.name_exists(schedule_name):
            raise ValidationError(
                f"Schedule name '{schedule_name}' already exists",
                detail={"field": "schedule_name"},
            )

        # Create Run and Schedule records (status: Running)
        parameters = {
            "max_per_day": max_per_day,
            "avoid_back_to_back": avoid_back_to_back,
            "max_days": max_days,
        }

        schedule, run = self.schedule_repo.create_schedule_with_run(
            schedule_name=schedule_name,
            dataset_id=dataset_id,
            user_id=user_id,
            algorithm_name="DSATUR",
            parameters=parameters,
        )

        try:
            files = await self.dataset_service.get_dataset_files(dataset_id, user_id)

            course_mapping = await self._ensure_courses_exist(
                dataset_id, files["courses"]
            )
            room_mapping = await self._ensure_rooms_exist(dataset_id, files["rooms"])

            graph = DSATURExamGraph(
                files["courses"], files["enrollments"], files["rooms"]
            )
            graph.build_graph()
            graph.dsatur_color()
            graph.dsatur_schedule(
                max_days=max_days,
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

            # total_conflicts, conflict_details, breakdown_df = (
            #     graph.count_schedule_conflicts()
            # )
            #
            # if not breakdown_df.empty:
            #     try:
            #         await self._save_conflicts(
            #             schedule_id=schedule.schedule_id, breakdown_df=breakdown_df
            #         )
            #     except Exception as db_error:
            #         self.schedule_repo.db.rollback()
            #         raise ScheduleGenerationError(
            #             f"Failed to save exam assignments: {str(db_error)}"
            #         ) from db_error

            self.run_repo.update_status(run.run_id, StatusEnum.Completed)

            summary = graph.summary()
            # fail_report = graph.fail_report()

            # Get dataset info for response
            dataset_info = self.dataset_service.get_dataset_info(dataset_id, user_id)

            return {
                "schedule_id": str(schedule.schedule_id),
                "schedule_name": schedule.schedule_name,
                "dataset_id": str(dataset_id),
                "dataset_name": dataset_info["dataset_name"],
                "summary": summary,
                # "conflicts": {
                #     "total": total_conflicts,
                #     "breakdown": breakdown_df.to_dict(orient="records")
                #     if not breakdown_df.empty
                #     else [],
                #     "details": {str(k): v for k, v in conflict_details.items()}
                #     if conflict_details
                #     else {},
                # },
                "conflicts": {
                    "total": 0,
                    "breakdown": [],
                    "details": {},
                },
                "failures": [],
                "schedule": {
                    "complete": results_df.to_dict(orient="records"),
                    "calendar": self._build_calendar_structure(results_df),
                    "total_exams": len(results_df),
                },
                "parameters": parameters,
            }

        except DatasetNotFoundError:
            # Re-raise dataset errors
            self.run_repo.update_status(run.run_id, StatusEnum.Failed)
            raise
        except Exception as e:
            # Update run status to Failed
            self.schedule_repo.db.rollback()
            self.run_repo.update_status(run.run_id, StatusEnum.Failed)
            raise ScheduleGenerationError(
                f"Schedule generation failed: {str(e)}"
            ) from e

    async def _ensure_courses_exist(
        self, dataset_id: UUID, courses_df: pd.DataFrame
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
            mapping = {
                course.course_subject_code: course.course_id
                for course in existing_courses
            }
            return mapping

        # Create new course records
        return self.course_repo.bulk_create_from_dataframe(dataset_id, courses_df)

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
            course_ref = row["Course"]
            room_name = row["Room"]

            # Get course_id from mapping
            course_id = course_mapping.get(course_ref)
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

    async def _save_conflicts(
        self, schedule_id: UUID, breakdown_df: pd.DataFrame
    ) -> None:
        """
        Save conflicts to database.

        Converts conflict breakdown DataFrame to Conflict records.
        Note: This requires student_id to be UUID in your database.
        """
        conflicts = []

        for _, row in breakdown_df.iterrows():
            conflicts.append(
                {
                    "student_id": str(row["Student_PIDM"]),
                    "exam_assignment_ids": [],
                    "conflict_type": row["conflict_type"],
                }
            )

        if conflicts:
            self.conflict_repo.bulk_create(schedule_id, conflicts)

    def list_schedules_for_user(
        self, user_id: UUID, skip: int = 0, limit: int = 100
    ) -> list[dict[str, Any]]:
        """
        List all schedules for user with metadata.

        Returns lightweight schedule info for list views.
        """
        schedules = self.schedule_repo.get_all_for_user(user_id, skip, limit)

        result = []
        for s in schedules:
            # Get counts
            exam_count = self.schedule_repo.get_exam_assignments_count(s.schedule_id)
            conflict_count = self.schedule_repo.get_conflicts_count(s.schedule_id)

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
                    "total_conflicts": conflict_count,
                }
            )

        return result

    async def delete_schedule(self, schedule_id: UUID, user_id: UUID) -> dict[str, Any]:
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

    def get_schedule_detail(
        self, schedule_id: UUID, user_id: UUID
    ) -> dict[Any, Any] | None:
        """
        Get detailed schedule information.

        Returns summary without loading all exam data.
        """
        return self.schedule_repo.get_schedule_summary(schedule_id, user_id)

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
