import datetime
import enum
import uuid
from typing import Any

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Time,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.mutable import MutableDict, MutableList
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class StatusEnum(enum.Enum):
    Running = "Running"
    Completed = "Completed"
    Failed = "Failed"


class DayEnum(enum.Enum):
    Monday = "Monday"
    Tuesday = "Tuesday"
    Wednesday = "Wednesday"
    Thursday = "Thursday"
    Friday = "Friday"
    Saturday = "Saturday"
    Sunday = "Sunday"


class Users(Base):
    """
    User accounts for authentication and authorization.

    Owns datasets and runs - ensures users can only access their own data.
    Supports role-based access (admin/user) and approval workflow.
    """

    __tablename__ = "users"
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(
        String(20), default="user", nullable=False
    )  # "admin" or "user"
    status: Mapped[str] = mapped_column(
        String(20), default="pending", nullable=False
    )  # "pending", "approved", "rejected"
    invited_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.user_id"), nullable=True
    )
    invited_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime, nullable=True
    )
    approved_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime, nullable=True
    )
    approved_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.user_id"), nullable=True
    )
    datasets: Mapped[list["Datasets"]] = relationship(
        "Datasets", back_populates="user", lazy="select"
    )
    runs: Mapped[list["Runs"]] = relationship(
        "Runs", back_populates="user", lazy="select"
    )
    # Relationships for invitations and approvals
    invited_users: Mapped[list["Users"]] = relationship(
        "Users",
        foreign_keys=[invited_by],
        remote_side=[user_id],
        lazy="select",
    )
    approved_users: Mapped[list["Users"]] = relationship(
        "Users",
        foreign_keys=[approved_by],
        remote_side=[user_id],
        lazy="select",
    )


class Datasets(Base):
    """
    Metadata catalog for uploaded CSV files stored on S3.

    Stores on simple storage (S3,etc) keys for courses, enrollments, and rooms CSV files.
    Does NOT store the actual CSV data - files remain on external storage (if not deleted).

    Links to user (ownership).
    """

    __tablename__ = "datasets"
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    dataset_name: Mapped[str] = mapped_column(String(255))
    upload_date: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.now
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.user_id"))
    file_paths: Mapped[list[dict]] = mapped_column(
        MutableList.as_mutable(JSONB), nullable=False
    )
    user: Mapped["Users"] = relationship(
        "Users", back_populates="datasets", lazy="select"
    )
    # Soft delete on db to maintain consistency, data will be deleted from external storage
    deleted_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime, nullable=True, default=None
    )
    courses: Mapped[list["Courses"]] = relationship(
        "Courses",
        back_populates="dataset",
        lazy="select",
        cascade="all, delete-orphan",
    )
    rooms: Mapped[list["Rooms"]] = relationship(
        "Rooms",
        back_populates="dataset",
        lazy="select",
        cascade="all, delete-orphan",
    )
    time_slots: Mapped[list["TimeSlots"]] = relationship(
        "TimeSlots",
        back_populates="dataset",
        lazy="select",
        cascade="all, delete-orphan",
    )
    runs: Mapped[list["Runs"]] = relationship(
        "Runs",
        back_populates="dataset",
        lazy="select",
    )


class Courses(Base):
    """
    Course catalog extracted from census CSV.

    Links to ExamAssignments to identify which course is scheduled when/where.
    """

    __tablename__ = "courses"
    course_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    crn: Mapped[str] = mapped_column(String(50), nullable=False)
    course_subject_code: Mapped[str] = mapped_column(String)
    instructor_name: Mapped[str | None] = mapped_column(String, nullable=True)
    department: Mapped[str | None] = mapped_column(String, nullable=True)
    examination_term: Mapped[str | None] = mapped_column(String, nullable=True)
    enrollment_count: Mapped[int] = mapped_column(Integer)
    dataset_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("datasets.dataset_id"))
    exam_assignments: Mapped[list["ExamAssignments"]] = relationship(
        "ExamAssignments", lazy="select", back_populates="course"
    )
    dataset: Mapped["Datasets"] = relationship(
        "Datasets", back_populates="courses", lazy="select"
    )


class Rooms(Base):
    """
    Classroom inventory extracted from rooms CSV.

    Duplicates data from CSV for faster queries without loading from external storage.
    Links to ExamAssignments to identify which room is used for each exam.
    """

    __tablename__ = "rooms"
    room_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    location: Mapped[str] = mapped_column(String(50))
    dataset_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("datasets.dataset_id"))
    dataset: Mapped["Datasets"] = relationship(
        "Datasets",
        back_populates="rooms",
        lazy="select",
    )
    exam_assignments: Mapped[list["ExamAssignments"]] = relationship(
        "ExamAssignments", back_populates="room", lazy="select"
    )


class TimeSlots(Base):
    """
    Time slot definitions generated during schedule creation.

    Maps DSATUR algorithm output (day_index, block_index) to actual times.
    Not in CSV - created dynamically by the algorithm.

    Example: Day=Monday, Block=0 → 9:00 AM - 11:00 AM
    """

    __tablename__ = "time_slots"
    time_slot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    slot_label: Mapped[str] = mapped_column(String(20))
    day: Mapped[DayEnum] = mapped_column(Enum(DayEnum))
    start_time: Mapped[datetime.time] = mapped_column(Time)
    end_time: Mapped[datetime.time] = mapped_column(Time)
    dataset_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("datasets.dataset_id"))
    dataset: Mapped["Datasets"] = relationship(
        "Datasets", back_populates="time_slots", lazy="select"
    )
    exam_assignments: Mapped[list["ExamAssignments"]] = relationship(
        "ExamAssignments", back_populates="time_slot", lazy="select"
    )


class Runs(Base):
    """
    Algorithm execution history and tracking.

    Records each time the scheduling algorithm runs:
    - Which dataset was used
    - What algorithm (DSATUR) and parameters
    - Current status (Running, Completed, Failed)
    - Created at timestamp

    """

    __tablename__ = "runs"
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    dataset_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("datasets.dataset_id"))
    run_timestamp: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.now
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.user_id"))
    algorithm_name: Mapped[str] = mapped_column(String(50))
    parameters: Mapped[dict[str, Any]] = mapped_column(
        MutableDict.as_mutable(JSONB), nullable=True
    )
    status: Mapped[StatusEnum] = mapped_column(Enum(StatusEnum))
    schedules: Mapped[list["Schedules"]] = relationship(
        "Schedules", lazy="select", back_populates="run"
    )
    dataset: Mapped["Datasets"] = relationship("Datasets", lazy="select")
    user: Mapped["Users"] = relationship("Users", lazy="select")


class Schedules(Base):
    """
    Generated exam schedule metadata.

    Contains schedule name and links to:
    - Run (how it was generated)
    - ExamAssignments (the actual exam placements)
    - ConflictAnalysis (conflict report)
    """

    __tablename__ = "schedules"
    schedule_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    schedule_name: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.now
    )
    run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("runs.run_id"))
    run: Mapped["Runs"] = relationship(
        "Runs", lazy="select", back_populates="schedules"
    )
    exam_assignments: Mapped[list["ExamAssignments"]] = relationship(
        "ExamAssignments",
        lazy="select",
        back_populates="schedule",
        cascade="all, delete-orphan",
    )
    conflict_analyses: Mapped["ConflictAnalyses"] = relationship(
        "ConflictAnalyses",
        lazy="select",
        back_populates="schedule",
        cascade="all, delete-orphan",
        uselist=False,
    )
    shares: Mapped[list["ScheduleShares"]] = relationship(
        "ScheduleShares",
        foreign_keys="[ScheduleShares.schedule_id]",
        lazy="select",
        cascade="all, delete-orphan",
    )


class ExamAssignments(Base):
    """
    The actual exam schedule - which exam is scheduled when and where.

    This is the core output of the scheduling algorithm.
    Each record represents: Course X has exam at TimeSlot Y in Room Z.

    Links to:
    - Course (what's being examined)
    - TimeSlot (when the exam happens)
    - Room (where the exam happens)
    - Schedule (which schedule this belongs to)
    """

    __tablename__ = "exam_assignments"
    exam_assignment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    course_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("courses.course_id"))
    time_slot_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("time_slots.time_slot_id")
    )
    room_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("rooms.room_id"))
    schedule_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("schedules.schedule_id"))
    course: Mapped["Courses"] = relationship(
        "Courses",
        lazy="select",
        back_populates="exam_assignments",
    )
    time_slot: Mapped["TimeSlots"] = relationship("TimeSlots", lazy="select")
    room: Mapped["Rooms"] = relationship("Rooms", lazy="select")
    schedule: Mapped["Schedules"] = relationship(
        "Schedules", lazy="select", back_populates="exam_assignments"
    )


class ConflictAnalyses(Base):
    """
    Stores complete conflict analysis from DSATUR algorithm as JSON.

    One record per schedule - contains all conflicts and statistics.

    JSON structure:
    {
      "hard_conflicts": {
        "student_double_book": [
          {"entity_id": "2003575", "day": "Monday", "block": 0,
           "crn": "10001", "conflicting_crn": "10002"},
          ...
        ],
        "instructor_double_book": [...],
        "student_gt_max_per_day": [...],
        "instructor_gt_max_per_day": [...]
      },
      "soft_conflicts": {
        "back_to_back_students": [
          {"student_id": "2037533", "day": "Monday", "blocks": [1, 2]},
          ...
        ],
        "back_to_back_instructors": [...],
        "large_courses_not_early": [...]
      },
      "statistics": {
        "student_double_book_count": 15,
        "instructor_double_book_count": 2,
        "total_hard_conflicts": 20,
        "total_soft_conflicts": 140
      }
    }
    """

    __tablename__ = "conflict_analyses"

    analysis_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    schedule_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("schedules.schedule_id"), unique=True, nullable=False
    )
    conflicts: Mapped[dict[str, Any]] = mapped_column(
        MutableDict.as_mutable(JSONB), nullable=False, default=dict
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.now
    )

    schedule: Mapped["Schedules"] = relationship(
        "Schedules", lazy="select", back_populates="conflict_analyses"
    )


class ScheduleShares(Base):
    """
    Schedule sharing permissions.

    Allows schedule owners to share schedules with other users
    with either view (read-only) or edit (can modify) permissions.
    """

    __tablename__ = "schedule_shares"
    share_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    schedule_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("schedules.schedule_id"), nullable=False
    )
    shared_with_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.user_id"), nullable=False
    )
    permission: Mapped[str] = mapped_column(
        String(10), nullable=False
    )  # "view" or "edit"
    shared_by_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.user_id"), nullable=False
    )
    shared_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.now
    )

    # Relationships
    schedule: Mapped["Schedules"] = relationship(
        "Schedules", foreign_keys=[schedule_id], lazy="select"
    )
    shared_with_user: Mapped["Users"] = relationship(
        "Users", foreign_keys=[shared_with_user_id], lazy="select"
    )
    shared_by_user: Mapped["Users"] = relationship(
        "Users", foreign_keys=[shared_by_user_id], lazy="select"
    )
