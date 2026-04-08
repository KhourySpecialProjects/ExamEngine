from collections import defaultdict
from typing import Any
from uuid import UUID

from src.core.exceptions import (
    DatasetNotFoundError,
    ScheduleGenerationError,
    ValidationError,
)
from src.domain.assemblers import ConflictAssembler, ScheduleAssembler
from src.domain.constants import (
    BLOCK_TIMES,
    DAY_NAMES,
)
from src.domain.factories import DatasetFactory
from src.domain.models import Course, Room
from src.domain.services.schedule_analyzer import ScheduleAnalysis, ScheduleAnalyzer
from src.domain.services.scheduler import Scheduler, ScheduleResult
from src.repo.conflict_analyses import ConflictAnalysesRepo
from src.repo.course import CourseRepo
from src.repo.exam_assignment import ExamAssignmentRepo
from src.repo.room import RoomRepo
from src.repo.run import RunRepo
from src.repo.schedule import ScheduleRepo
from src.repo.schedule_share import ScheduleShareRepo
from src.repo.time_slot import TimeSlotRepo
from src.schemas.db import StatusEnum
from src.services.dataset.service import DatasetService
from src.services.schedule.permissions import SchedulePermissionService


class ScheduleService:
    """
    Business logic for exam schedule generation and management.

    Orchestrates:
    1. Schedule generation workflow (dataset → algorithm → persistence)
    2. Schedule retrieval and formatting
    3. Schedule listing with permissions

    Delegates to:
    - SchedulePermissionService: ownership/sharing checks
    - ScheduleResponseBuilder: API response formatting
    - ScheduleAnalyzer: conflict analysis (domain)
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

        # Initialize permission service
        share_repo = ScheduleShareRepo(schedule_repo.db)
        self._permissions = SchedulePermissionService(share_repo)

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
        """Generate complete exam schedule from dataset."""

        if self.schedule_repo.name_exists(schedule_name, user_id):
            raise ValidationError(
                f"Schedule name '{schedule_name}' already exists",
                detail={"field": "schedule_name"},
            )
        parameters = {
            "student_max_per_day": student_max_per_day,
            "instructor_max_per_day": instructor_max_per_day,
            "avoid_back_to_back": avoid_back_to_back,
            "max_days": max_days,
            "prioritize_large_courses": prioritize_large_courses,
        }

        # 1. Create schedule and run records
        schedule, run = self.schedule_repo.create_schedule_with_run(
            schedule_name=schedule_name,
            dataset_id=dataset_id,
            user_id=user_id,
            algorithm_name="DSATUR",
            parameters=parameters,
        )

        try:
            # 2. Load dataset files
            files = await self.dataset_service.get_dataset_files(dataset_id, user_id)

            # 3. Load course merges (if any) - synchronous call
            merges = self.dataset_service.get_merges(dataset_id, user_id) or {}

            # 3.5 Drop zero-enrollment courses and get updated merges
            files = await self.dataset_service.drop_zero_enrollment(dataset_id, user_id)

            # 4. Build scheduling dataset and run algorithm
            scheduling_dataset = DatasetFactory.from_dataframes_to_scheduling_dataset(
                courses_df=files["courses"],
                enrollment_df=files["enrollments"],
                rooms_df=files["rooms"],
            )

            # 5. Ensure database records exist for courses/rooms
            course_mapping = self._ensure_courses(
                dataset_id,
                scheduling_dataset.courses,
            )
            room_mapping = self._ensure_rooms(
                dataset_id,
                scheduling_dataset.rooms,
            )

            scheduler = Scheduler(
                dataset=scheduling_dataset,
                max_days=max_days,
                student_max_per_day=student_max_per_day,
                instructor_max_per_day=instructor_max_per_day,
                merges=merges,  # Pass merges to scheduler
            )
            result = scheduler.schedule(
                prioritize_large_courses=prioritize_large_courses
            )

            # 5. Analyze results
            analyzer = ScheduleAnalyzer(scheduling_dataset)
            analysis = analyzer.analyze(schedule=result)

            # 6. Persist results
            await self._save_exam_assignments(
                schedule.schedule_id,
                dataset_id,
                result,
                course_mapping,
                room_mapping,
                merges,
            )
            conflicts_response = await self._save_and_format_conflicts(
                schedule.schedule_id, analysis
            )

            # 7. Mark complete
            self.run_repo.update_status(run.run_id, StatusEnum.Completed)

            # 8. Build response
            return self._build_generation_response(
                schedule,
                dataset_id,
                user_id,
                result,
                scheduling_dataset,
                conflicts_response,
                parameters,
            )

        except DatasetNotFoundError:
            self.run_repo.update_status(run.run_id, StatusEnum.Failed)
            raise
        except Exception as e:
            self.schedule_repo.db.rollback()
            self.run_repo.update_status(run.run_id, StatusEnum.Failed)
            raise ScheduleGenerationError(f"Schedule generation failed: {e}") from e

    async def list_schedules_for_user(self, user_id: UUID) -> list[dict[str, Any]]:
        """List all schedules for user with metadata and permissions."""
        schedules = self.schedule_repo.get_all_for_user(user_id)

        return [
            ScheduleAssembler.build_list_item(
                schedule=s,
                exam_count=self.schedule_repo.get_exam_assignments_count(s.schedule_id),
                permissions=self._permissions.get_permissions(s, user_id),
            )
            for s in schedules
        ]

    async def get_schedule_with_details(
        self, schedule_id: UUID, user_id: UUID
    ) -> dict[str, Any] | None:
        """Get complete schedule details including exams and conflicts."""
        schedule = self.schedule_repo.get_with_run_details(schedule_id, user_id)
        if not schedule:
            return None

        # Load related data (includes unscheduled assignments with NULL time_slot/room)
        assignments = self.exam_assignment_repo.get_all_for_schedule(schedule_id)
        conflict_analysis = self.conflict_analyses_repo.get_by_schedule_id(schedule_id)
        permissions = self._permissions.get_permissions(schedule, user_id)

        # Build course name map for conflict enrichment
        course_map = {
            str(a.course.crn): a.course.course_subject_code for a in assignments
        }
        formatter = ConflictAssembler(course_map)
        conflicting_crns = formatter.get_conflicting_crns(conflict_analysis)

        # Build schedule data
        calendar, complete_exams = self._build_schedule_data(
            assignments, conflicting_crns
        )
        conflicts = formatter.format_conflicts(conflict_analysis)
        summary = self._calculate_summary_stats(assignments, conflicts)

        return ScheduleAssembler.build_full_response(
            schedule=schedule,
            dataset_name=schedule.run.dataset.dataset_name,
            summary=summary,
            conflicts=conflicts,
            schedule_block=ScheduleAssembler.build_schedule_block(
                complete_exams, calendar
            ),
            permissions=permissions,
        )

    async def delete_schedule(self, schedule_id: UUID, user_id: UUID) -> dict[str, Any]:
        """Delete schedule and all related data."""
        success = self.schedule_repo.delete_schedule_cascade(schedule_id, user_id)

        if not success:
            raise DatasetNotFoundError(
                f"Schedule {schedule_id} not found or access denied"
            )

        return {"message": "Schedule deleted", "schedule_id": str(schedule_id)}

    def _build_schedule_data(
        self,
        assignments: list,
        conflicting_crns: set[str],
    ) -> tuple[dict[str, dict[str, list[dict]]], list[dict]]:
        """Build calendar and complete exam list from assignments."""
        calendar: dict[str, dict[str, list]] = defaultdict(lambda: defaultdict(list))
        complete_exams = []

        for assignment in assignments:
            crn = str(assignment.course.crn)
            has_conflict = crn in conflicting_crns

            # Check if assignment is unscheduled (no time_slot or room)
            is_unscheduled = assignment.time_slot is None or assignment.room is None

            if is_unscheduled:
                # Build unscheduled exam record (no Day, Block, or Room)
                complete_exams.append(
                    {
                        "CRN": crn,
                        "Course": assignment.course.course_subject_code,
                        "Day": "",  # Empty for unscheduled
                        "Block": "",  # Empty for unscheduled
                        "Room": "",  # Empty for unscheduled
                        "Capacity": 0,
                        "Size": assignment.course.enrollment_count,
                        "Valid": not has_conflict,
                        "Instructor": assignment.course.instructor_name or "",
                    }
                )
            else:
                # Full exam record for 'complete' list
                complete_exams.append(
                    ScheduleAssembler.build_exam_record_from_assignment(
                        assignment, has_conflict
                    )
                )

                # Calendar entry (grouped by day/slot) - only for scheduled exams
                day = assignment.time_slot.day.value
                slot_label = assignment.time_slot.slot_label
                calendar[day][slot_label].append(
                    ScheduleAssembler.build_calendar_entry_from_assignment(
                        assignment, has_conflict
                    )
                )

        return dict(calendar), complete_exams

    def _calculate_summary_stats(
        self,
        assignments: list,
        conflicts: dict[str, Any],
    ) -> dict[str, Any]:
        """Calculate summary statistics from assignments."""
        # Count unique values (only for scheduled assignments)
        unique_rooms = {a.room.location for a in assignments if a.room is not None}
        unique_slots = {
            (a.time_slot.day.value, a.time_slot.slot_label)
            for a in assignments
            if a.time_slot is not None
        }

        # Estimate students (we don't have full enrollment data in assignments)
        total_enrollment = sum(a.course.enrollment_count for a in assignments)

        # Count unscheduled exams
        unscheduled_count = sum(
            1 for a in assignments if a.time_slot is None or a.room is None
        )

        return ScheduleAssembler.build_summary(
            num_classes=len(assignments),
            num_students=total_enrollment,  # Approximation
            num_rooms=len(unique_rooms),
            slots_used=len(unique_slots),
            hard_conflicts=conflicts.get("total", 0),
            unplaced_exams=unscheduled_count,
        )

    def _build_generation_response(
        self,
        schedule,
        dataset_id: UUID,
        user_id: UUID,
        result: ScheduleResult,
        scheduling_dataset,
        conflicts_response: dict,
        parameters: dict,
        merges: dict[str, list[str]] = None,
    ) -> dict[str, Any]:
        """Build response for generate_schedule endpoint."""
        # Count unique students
        all_students = set()
        for crn in result.assignments:
            students = scheduling_dataset.students_by_crn.get(crn, frozenset())
            all_students.update(students)

        slots_used = len(set(result.assignments.values()))
        rooms_used = len(set(result.room_assignments.values()))

        # Build schedule list (scheduled exams only)
        schedule_list = []
        for crn, (day_idx, block_idx) in result.assignments.items():
            room_name = result.room_assignments.get(crn, "TBD")
            instructors = result.instructors_by_crn.get(crn, set())

            schedule_list.append(
                ScheduleAssembler.build_exam_record(
                    crn=crn,
                    course_code=result.course_codes.get(crn, ""),
                    day=DAY_NAMES[day_idx],
                    block_label=f"{block_idx} ({BLOCK_TIMES.get(block_idx, '')})",
                    room=room_name,
                    capacity=result.room_capacities.get(room_name, 0),
                    size=result.course_sizes.get(crn, 0),
                    instructor=", ".join(instructors) if instructors else "",
                    has_conflict=False,  # Conflicts tracked separately
                )
            )

        # Add unscheduled merge exams to complete list
        for merge_id in result.unscheduled_merges:
            crns = merges.get(merge_id, [])
            for crn in crns:
                if crn in scheduling_dataset.courses:
                    course = scheduling_dataset.courses[crn]
                    instructors = result.instructors_by_crn.get(crn, set())
                    schedule_list.append(
                        {
                            "CRN": crn,
                            "Course": result.course_codes.get(crn, course.course_code),
                            "Day": "",  # Empty for unscheduled
                            "Block": "",  # Empty for unscheduled
                            "Room": "",  # Empty for unscheduled
                            "Capacity": 0,
                            "Size": result.course_sizes.get(
                                crn, course.enrollment_count
                            ),
                            "Valid": True,
                            "Instructor": ", ".join(instructors) if instructors else "",
                        }
                    )

        # Build calendar
        calendar = self._build_calendar_from_result(result)

        # Get dataset info
        dataset_info = self.dataset_service.get_dataset_info(dataset_id, user_id)

        summary = ScheduleAssembler.build_summary(
            num_classes=len(result.assignments),
            num_students=len(all_students),
            num_rooms=rooms_used,
            slots_used=slots_used,
            hard_conflicts=conflicts_response["total_hard"],
            unplaced_exams=len(result.unassigned),
        )

        return ScheduleAssembler.build_generation_response(
            schedule=schedule,
            dataset_id=dataset_id,
            dataset_name=dataset_info["dataset_name"],
            schedule_list=schedule_list,
            calendar=calendar,
            summary=summary,
            conflicts=conflicts_response["conflicts"],
            parameters=parameters,
        )

    def _build_calendar_from_result(self, result: ScheduleResult) -> dict:
        """Build calendar structure from algorithm result."""
        calendar: dict[str, dict[str, list]] = {}

        for crn, (day_idx, block_idx) in result.assignments.items():
            day_name = DAY_NAMES[day_idx]
            block_time = BLOCK_TIMES.get(block_idx, f"Block {block_idx}")

            if day_name not in calendar:
                calendar[day_name] = {}
            if block_time not in calendar[day_name]:
                calendar[day_name][block_time] = []

            room_name = result.room_assignments.get(crn, "TBD")
            instructors = result.instructors_by_crn.get(crn, set())

            calendar[day_name][block_time].append(
                ScheduleAssembler.build_calendar_entry(
                    crn=crn,
                    course_code=result.course_codes.get(crn, ""),
                    room=room_name,
                    capacity=result.room_capacities.get(room_name, 0),
                    size=result.course_sizes.get(crn, 0),
                    instructor=", ".join(instructors) if instructors else "",
                )
            )

        return calendar

    # Persistence
    def _ensure_courses(
        self,
        dataset_id: UUID,
        courses: dict[str, Course],
    ) -> dict[str, UUID]:
        """Ensure course records exist, return CRN -> course_id mapping."""
        existing = self.course_repo.get_all_for_dataset(dataset_id)
        if existing:
            return {c.crn: c.course_id for c in existing}
        return self.course_repo.bulk_create_from_domain(dataset_id, courses)

    def _ensure_rooms(
        self,
        dataset_id: UUID,
        rooms: list[Room],
    ) -> dict[str, UUID]:
        """Ensure room records exist, return room_name -> room_id mapping."""
        existing = self.room_repo.get_all_for_dataset(dataset_id)
        if existing:
            return {r.location: r.room_id for r in existing}
        return self.room_repo.bulk_create_from_domain(dataset_id, rooms)

    async def _save_exam_assignments(
        self,
        schedule_id: UUID,
        dataset_id: UUID,
        result: ScheduleResult,
        course_mapping: dict[str, UUID],
        room_mapping: dict[str, UUID],
        merges: dict[str, list[str]],
    ) -> None:
        """Save exam assignments from ScheduleResult to database."""
        assignments_to_create = []

        # Save scheduled assignments (with time slots and rooms)
        for crn, (day_idx, block_idx) in result.assignments.items():
            course_id = course_mapping.get(crn)
            if not course_id:
                continue

            room_name = result.room_assignments.get(crn)
            if not room_name:
                continue

            room_id = room_mapping.get(room_name)
            if not room_id:
                continue

            time_slot = self.time_slot_repo.get_or_create_slot(
                dataset_id=dataset_id,
                day=DAY_NAMES[day_idx],
                block_index=block_idx,
            )

            assignments_to_create.append(
                {
                    "course_id": course_id,
                    "time_slot_id": time_slot.time_slot_id,
                    "room_id": room_id,
                }
            )

        # Save unscheduled merge assignments (without time slots or rooms)
        for merge_id in result.unscheduled_merges:
            crns = merges.get(merge_id, [])
            for crn in crns:
                course_id = course_mapping.get(crn)
                if not course_id:
                    continue

                # Create assignment without time_slot_id or room_id
                assignments_to_create.append(
                    {
                        "course_id": course_id,
                        "time_slot_id": None,
                        "room_id": None,
                    }
                )

        if assignments_to_create:
            self.exam_assignment_repo.bulk_create(schedule_id, assignments_to_create)

    async def _save_and_format_conflicts(
        self, schedule_id: UUID, analysis: ScheduleAnalysis
    ) -> dict:
        """Save conflicts to database and return formatted response."""
        conflict_payload = analysis.to_dict()

        try:
            self.conflict_analyses_repo.create_analysis(
                schedule_id=schedule_id,
                conflicts_data=conflict_payload,
            )
        except Exception as e:
            raise e

        return {
            "total_hard": analysis.statistics.total_hard_conflicts,
            "total_soft": analysis.statistics.total_soft_conflicts,
            "conflicts": conflict_payload,
        }
