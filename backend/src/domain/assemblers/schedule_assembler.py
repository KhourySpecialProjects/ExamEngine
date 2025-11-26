from typing import Any
from uuid import UUID

from src.domain.value_objects import SchedulePermissions


class ScheduleAssembler:
    """
    Builds consistent API responses for schedule endpoints.

    """

    @staticmethod
    def build_exam_record(
        crn: str,
        course_code: str,
        day: str,
        block_label: str,
        room: str,
        capacity: int,
        size: int,
        instructor: str,
        has_conflict: bool = False,
    ) -> dict[str, Any]:
        """
        Build standard exam record for 'complete' list.

        Used by both generate_schedule and get_schedule_with_details.
        """
        return {
            "CRN": crn,
            "Course": course_code,
            "Day": day,
            "Block": block_label,
            "Room": room,
            "Capacity": capacity,
            "Size": size,
            "Valid": not has_conflict,
            "Instructor": instructor,
        }

    @staticmethod
    def build_exam_record_from_assignment(
        assignment, has_conflict: bool = False
    ) -> dict[str, Any]:
        """
        Build exam record from ExamAssignment ORM object.

        Convenience method for retrieval paths.
        """
        return ScheduleAssembler.build_exam_record(
            crn=assignment.course.crn,
            course_code=assignment.course.course_subject_code,
            day=assignment.time_slot.day.value,
            block_label=assignment.time_slot.slot_label,
            room=assignment.room.location,
            capacity=assignment.room.capacity,
            size=assignment.course.enrollment_count,
            instructor=assignment.course.instructor_name or "",
            has_conflict=has_conflict,
        )

    @staticmethod
    def build_calendar_entry(
        crn: str,
        course_code: str,
        room: str,
        capacity: int,
        size: int,
        instructor: str,
        has_conflict: bool = False,
    ) -> dict[str, Any]:
        """
        Build calendar cell entry (subset of exam record, no day/block).

        Used for nested calendar structure where day/block are keys.
        """
        return {
            "CRN": crn,
            "Course": course_code,
            "Room": room,
            "Capacity": capacity,
            "Size": size,
            "Valid": not has_conflict,
            "Instructor": instructor,
        }

    @staticmethod
    def build_calendar_entry_from_assignment(
        assignment, has_conflict: bool = False
    ) -> dict[str, Any]:
        """Build calendar entry from ExamAssignment ORM object."""
        return ScheduleAssembler.build_calendar_entry(
            crn=assignment.course.crn,
            course_code=assignment.course.course_subject_code,
            room=assignment.room.location,
            capacity=assignment.room.capacity,
            size=assignment.course.enrollment_count,
            instructor=assignment.course.instructor_name or "",
            has_conflict=has_conflict,
        )

    @staticmethod
    def build_summary(
        num_classes: int,
        num_students: int,
        num_rooms: int,
        slots_used: int,
        hard_conflicts: int,
        unplaced_exams: int = 0,
    ) -> dict[str, Any]:
        """
        Build schedule summary statistics.

        Consistent format for both generation and retrieval.
        """
        return {
            "num_classes": num_classes,
            "num_students": num_students,
            "potential_overlaps": 0,  # Legacy field, kept for API compatibility
            "real_conflicts": hard_conflicts,
            "num_rooms": num_rooms,
            "slots_used": slots_used,
            "unplaced_exams": unplaced_exams,
        }

    @staticmethod
    def build_list_item(
        schedule,
        exam_count: int,
        permissions: SchedulePermissions,
    ) -> dict[str, Any]:
        """
        Build schedule list item for list endpoints.

        Lightweight format without full exam/conflict details.
        """
        return {
            "schedule_id": str(schedule.schedule_id),
            "schedule_name": schedule.schedule_name,
            "created_at": schedule.created_at.isoformat(),
            "algorithm": schedule.run.algorithm_name,
            "parameters": schedule.run.parameters,
            "status": schedule.run.status.value,
            "dataset_id": str(schedule.run.dataset_id),
            "total_exams": exam_count,
            **permissions.to_dict(),
        }

    @staticmethod
    def build_schedule_block(
        complete_exams: list[dict],
        calendar: dict[str, dict[str, list[dict]]],
    ) -> dict[str, Any]:
        """Build the 'schedule' block of the response."""
        return {
            "complete": complete_exams,
            "calendar": calendar,
            "total_exams": len(complete_exams),
        }

    @staticmethod
    def build_full_response(
        schedule,
        dataset_name: str,
        summary: dict[str, Any],
        conflicts: dict[str, Any],
        schedule_block: dict[str, Any],
        permissions: SchedulePermissions,
    ) -> dict[str, Any]:
        """
        Build complete schedule detail response.

        Used by get_schedule_with_details to ensure consistent shape.
        """
        return {
            "schedule_id": str(schedule.schedule_id),
            "schedule_name": schedule.schedule_name,
            "created_at": schedule.created_at.isoformat(),
            "dataset_id": str(schedule.run.dataset.dataset_id),
            "dataset_name": dataset_name,
            "summary": summary,
            "conflicts": conflicts,
            "failures": [],  # Legacy field
            "schedule": schedule_block,
            "parameters": schedule.run.parameters,
            "algorithm": schedule.run.algorithm_name,
            "status": schedule.run.status.value,
            **permissions.to_dict(),
        }

    @staticmethod
    def build_generation_response(
        schedule,
        dataset_id: UUID,
        dataset_name: str,
        schedule_list: list[dict],
        calendar: dict,
        summary: dict[str, Any],
        conflicts: dict[str, Any],
        parameters: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Build response for generate_schedule endpoint.

        Slightly different shape than detail response (no permissions).
        """
        return {
            "schedule_id": str(schedule.schedule_id),
            "schedule_name": schedule.schedule_name,
            "dataset_id": str(dataset_id),
            "dataset_name": dataset_name,
            "summary": summary,
            "conflicts": conflicts,
            "failures": [],
            "schedule": {
                "complete": schedule_list,
                "calendar": calendar,
                "total_exams": len(schedule_list),
            },
            "parameters": parameters,
        }
