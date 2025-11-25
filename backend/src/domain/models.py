from dataclasses import dataclass, field
from uuid import UUID


@dataclass(frozen=True)
class Course:
    """
    Canonical representation of a course section.

    This is what the rest of the application works with internally.
    All CSV formats are converted to this structure.
    """

    crn: str  # Course Registration Number (unique identifier)
    course_code: str  # e.g., "CS 4535"
    enrollment_count: int  # Number of students enrolled
    instructor_names: set[str] = field(
        default_factory=set
    )  # May be multiple instructors

    def __post_init__(self):
        """Validate data after initialization."""
        if not self.crn or not self.crn.strip():
            raise ValueError("CRN cannot be empty")
        if self.enrollment_count < 0:
            raise ValueError("Enrollment count cannot be negative")
        # Ensure instructor_names is a set (immutable due to frozen=True)
        if not isinstance(self.instructor_names, set):
            object.__setattr__(self, "instructor_names", set(self.instructor_names))


@dataclass(frozen=True)
class Student:
    """Canonical representation of a student."""

    student_id: str
    enrolled_crns: frozenset[str] = field(default_factory=frozenset)

    def __post_init__(self):
        """Validate and normalize data."""
        if not self.student_id or not self.student_id.strip():
            raise ValueError("Student ID cannot be empty")
        if not isinstance(self.enrolled_crns, frozenset):
            object.__setattr__(self, "enrolled_crns", frozenset(self.enrolled_crns))


@dataclass(frozen=True)
class Enrollment:
    """
    Represents a single student-course enrollment record.

    This is extracted from enrollment CSV and used to build
    both Student and Course objects with full relationships.
    """

    student_id: str
    crn: str
    instructor_name: str | None = None

    def __post_init__(self):
        """Validate data."""
        if not self.student_id or not self.student_id.strip():
            raise ValueError("Student ID cannot be empty")
        if not self.crn or not self.crn.strip():
            raise ValueError("CRN cannot be empty")


@dataclass(frozen=True)
class Room:
    """Canonical representation of an exam room."""

    name: str
    capacity: int

    def __post_init__(self):
        """Validate data."""
        if not self.name or not self.name.strip():
            raise ValueError("Room name cannot be empty")
        if self.capacity <= 0:
            raise ValueError("Room capacity must be positive")


@dataclass(frozen=True)
class TimeSlot:
    """Represents a specific exam time slot."""

    day: str  # e.g., "Monday", "Tuesday"
    block: str  # e.g., "9AM-11AM", "11:30AM-1:30PM"

    def __post_init__(self):
        """Validate data."""
        if not self.day or not self.day.strip():
            raise ValueError("Day cannot be empty")
        if not self.block or not self.block.strip():
            raise ValueError("Block cannot be empty")


@dataclass(frozen=True)
class ExamAssignment:
    """
    Represents a scheduled exam with all details.

    This is the output of the scheduling algorithm.
    """

    crn: str
    course_code: str
    time_slot: TimeSlot
    room: Room
    enrollment_count: int
    instructor_names: set[str] = field(default_factory=set)
    is_valid: bool = True  # False if there are conflicts

    def __post_init__(self):
        """Validate and normalize data."""
        if not self.crn or not self.crn.strip():
            raise ValueError("CRN cannot be empty")
        if not isinstance(self.instructor_names, set):
            object.__setattr__(self, "instructor_names", set(self.instructor_names))


@dataclass
class Dataset:
    """
    Complete dataset for exam scheduling.

    This aggregates all the data needed for scheduling in one place.
    """

    dataset_id: UUID
    name: str
    courses: dict[str, Course]  # Keyed by CRN
    students: dict[str, Student]  # Keyed by student_id
    rooms: list[Room]

    def get_course(self, crn: str) -> Course | None:
        """Safely retrieve a course by CRN."""
        return self.courses.get(crn)

    def get_student(self, student_id: str) -> Student | None:
        """Safely retrieve a student by ID."""
        return self.students.get(student_id)

    def validate(self) -> list[str]:
        """
        Validate dataset integrity and return list of warnings/errors.

        Returns empty list if dataset is valid.
        """
        issues = []

        # Check for courses with no students
        empty_courses = [
            crn for crn, course in self.courses.items() if course.enrollment_count == 0
        ]
        if empty_courses:
            issues.append(f"Found {len(empty_courses)} courses with zero enrollment")

        # Check for students enrolled in non-existent courses
        all_crns = set(self.courses.keys())
        for student in self.students.values():
            invalid_crns = student.enrolled_crns - all_crns
            if invalid_crns:
                issues.append(
                    f"Student {student.student_id} enrolled in non-existent "
                    f"courses: {invalid_crns}"
                )

        # Check for insufficient room capacity
        max_course_size = max(
            (c.enrollment_count for c in self.courses.values()), default=0
        )
        max_room_capacity = max((r.capacity for r in self.rooms), default=0)
        if max_course_size > max_room_capacity:
            issues.append(
                f"Largest course ({max_course_size} students) exceeds "
                f"largest room capacity ({max_room_capacity})"
            )

        return issues


@dataclass(frozen=True)
class SchedulingDataset:
    """
    Complete input for a scheduling problem.

    This is what the algorithm operates on—pure domain objects,
    no DataFrame knowledge, no CSV column awareness.
    """

    courses: dict[str, Course]  # CRN → Course
    students: dict[str, Student]  # student_id → Student
    rooms: list[Room]

    # Pre-computed relationships for algorithm efficiency
    students_by_crn: dict[str, frozenset[str]]  # CRN → {student_ids}
    instructors_by_crn: dict[str, frozenset[str]]  # CRN → {instructor_names}

    def get_course(self, crn: str) -> Course | None:
        return self.courses.get(crn)

    def get_enrollment_count(self, crn: str) -> int:
        """Helper for algorithm to get course size without knowing Course internals."""
        course = self.courses.get(crn)
        return course.enrollment_count if course else 0

    def get_shared_students(self, crn1: str, crn2: str) -> frozenset[str]:
        """Find students enrolled in both courses (for conflict graph edges)."""
        s1 = self.students_by_crn.get(crn1, frozenset())
        s2 = self.students_by_crn.get(crn2, frozenset())
        return s1 & s2
