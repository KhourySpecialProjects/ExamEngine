"""The ordered catalog of schedule validation checks."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

from src.domain.validation.checks import conflicts, coverage, data, groups, rooms
from src.domain.validation.context import ValidationContext
from src.domain.validation.results import CheckResult


Category = Literal["coverage", "rooms", "groups", "conflicts", "data"]


@dataclass(frozen=True)
class Check:
    id: str
    title: str
    description: str
    category: Category
    run: Callable[[ValidationContext], CheckResult]

    def to_dict(self) -> dict[str, str]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "category": self.category,
        }


# Run order. Ids are part of the API contract.
CHECKS: tuple[Check, ...] = (
    Check(
        "coverage.crn_single_row",
        "One exam per CRN",
        "No CRN appears more than once in the schedule.",
        "coverage",
        coverage.crn_single_row,
    ),
    Check(
        "coverage.crn_in_courses_file",
        "Scheduled CRNs exist",
        "Every CRN in the schedule is in the uploaded courses file.",
        "coverage",
        coverage.crn_in_courses_file,
    ),
    Check(
        "coverage.crn_accounted",
        "Every course accounted for",
        "Every course in the courses file is placed, unscheduled with a stated "
        "reason, or excluded for zero enrollment.",
        "coverage",
        coverage.crn_accounted,
    ),
    Check(
        "coverage.exams_have_rooms",
        "Placed exams have rooms",
        "Every exam with a time slot also has a room.",
        "coverage",
        coverage.exams_have_rooms,
    ),
    Check(
        "coverage.within_window",
        "Inside the exam window",
        "Every exam falls within the schedule's days and blocks per day.",
        "coverage",
        coverage.within_window,
    ),
    Check(
        "rooms.in_rooms_file",
        "Rooms exist",
        "Every room used is in the uploaded rooms file with the same capacity.",
        "rooms",
        rooms.in_rooms_file,
    ),
    Check(
        "rooms.capacity",
        "Room capacity",
        "No room seats more students than its capacity at any time.",
        "rooms",
        rooms.capacity,
    ),
    Check(
        "rooms.no_double_booking",
        "One exam per room",
        "No room holds two different exams at the same time.",
        "rooms",
        rooms.no_double_booking,
    ),
    Check(
        "rooms.blockouts",
        "Room blockouts respected",
        "No exam is placed in a room during one of its blocked-out times.",
        "rooms",
        rooms.blockouts,
    ),
    Check(
        "groups.combined_together",
        "Combined groups together",
        "All sections of a combined exam share one time slot and one room.",
        "groups",
        groups.combined_together,
    ),
    Check(
        "groups.common_same_slot",
        "Common groups in one slot",
        "All sections of a common exam share one time slot, each exam in its own room.",
        "groups",
        groups.common_same_slot,
    ),
    Check(
        "groups.unscheduled_consistent",
        "Unscheduled groups consistent",
        "Groups listed as unscheduled match the dataset, give a reason and have no "
        "placed exams.",
        "groups",
        groups.unscheduled_consistent,
    ),
    Check(
        "conflicts.student_double_book",
        "Student double-bookings",
        "Students with two exams at the same time, recomputed from the enrollments "
        "and compared with the stored analysis.",
        "conflicts",
        conflicts.student_double_book,
    ),
    Check(
        "conflicts.instructor_double_book",
        "Instructor double-bookings",
        "Instructors with two exams at the same time, recomputed and compared with "
        "the stored analysis.",
        "conflicts",
        conflicts.instructor_double_book,
    ),
    Check(
        "conflicts.student_over_max_per_day",
        "Student daily limit",
        "Students with more exams in a day than the schedule allows, recomputed and "
        "compared with the stored analysis.",
        "conflicts",
        conflicts.student_over_max_per_day,
    ),
    Check(
        "conflicts.instructor_over_max_per_day",
        "Instructor daily limit",
        "Instructors with more exams in a day than the schedule allows, recomputed "
        "and compared with the stored analysis.",
        "conflicts",
        conflicts.instructor_over_max_per_day,
    ),
    Check(
        "conflicts.student_back_to_back",
        "Student back-to-back exams",
        "Students with exams in consecutive blocks of a day, recomputed and "
        "compared with the stored analysis.",
        "conflicts",
        conflicts.student_back_to_back,
    ),
    Check(
        "conflicts.instructor_back_to_back",
        "Instructor back-to-back exams",
        "Instructors with exams in consecutive blocks of a day, recomputed and "
        "compared with the stored analysis.",
        "conflicts",
        conflicts.instructor_back_to_back,
    ),
    Check(
        "conflicts.large_course_late",
        "Large courses late in the week",
        "Large courses placed late in the week, recomputed and compared with the "
        "stored analysis.",
        "conflicts",
        conflicts.large_course_late,
    ),
    Check(
        "data.stored_course_matches_file",
        "Stored courses match the file",
        "Each scheduled course's stored enrollment and instructor match the "
        "courses file.",
        "data",
        data.stored_course_matches_file,
    ),
    Check(
        "data.stored_statistics",
        "Stored statistics",
        "The stored statistics agree with the stored conflicts and the schedule.",
        "data",
        data.stored_statistics,
    ),
    Check(
        "data.enrollment_totals",
        "Enrollment totals",
        "Each course's Total_Enrollment equals the number of students enrolled in it.",
        "data",
        data.enrollment_totals,
    ),
    Check(
        "data.enrollment_unknown_crns",
        "Enrollments for unknown courses",
        "Every enrollment row is for a CRN in the courses file.",
        "data",
        data.enrollment_unknown_crns,
    ),
    Check(
        "data.duplicates",
        "Duplicate rows",
        "No CRN is repeated in the courses file and no student is enrolled in the "
        "same CRN twice.",
        "data",
        data.duplicates,
    ),
)
