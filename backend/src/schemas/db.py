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
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Students(Base):
    __tablename__ = "students"
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    dataset_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("datasets.dataset_id"))


class Courses(Base):
    __tablename__ = "courses"
    course_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    course_subject_code: Mapped[str] = mapped_column(String)
    enrollment_count: Mapped[int] = mapped_column(Integer)
    dataset_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("datasets.dataset_id"))


class Conflicts(Base):
    __tablename__ = "conflicts"
    conflict_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    student_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("students.student_id"))
    exam_assignment_ids: Mapped[list[uuid.UUID]] = mapped_column(
        MutableList.as_mutable(JSONB),
        nullable=False,
        default=list,
    )
    conflict_type: Mapped[str] = mapped_column(String)
    schedule_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("schedules.schedule_id"))


class ExamAssignments(Base):
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


class Rooms(Base):
    __tablename__ = "rooms"
    room_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    location: Mapped[str] = mapped_column(String(50))
    dataset_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("datasets.dataset_id"))


class DayEnum(enum.Enum):
    Monday = "Monday"
    Tuesday = "Tuesday"
    Wednesday = "Wednesday"
    Thursday = "Thursday"
    Friday = "Friday"


class TimeSlots(Base):
    __tablename__ = "time_slots"
    time_slot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    slot_label: Mapped[str] = mapped_column(String(10))
    day: Mapped[DayEnum] = mapped_column(Enum(DayEnum))
    start_time: Mapped[datetime.time] = mapped_column(Time)
    end_time: Mapped[datetime.time] = mapped_column(Time)
    dataset_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("datasets.dataset_id"))


class Users(Base):
    __tablename__ = "users"
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)


class Schedules(Base):
    __tablename__ = "schedules"
    schedule_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    schedule_name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    created_at: Mapped[datetime.time] = mapped_column(
        DateTime, default=datetime.datetime.now
    )
    run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("runs.run_id"))


class Datasets(Base):
    __tablename__ = "datasets"
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    dataset_name: Mapped[str] = mapped_column(String(255))
    upload_date: Mapped[DateTime] = mapped_column(
        DateTime, default=datetime.datetime.now
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.user_id"))
    file_paths: Mapped[list[dict]] = mapped_column(
        MutableList.as_mutable(JSONB), nullable=False
    )


class StatusEnum(enum.Enum):
    Running = "Running"
    Completed = "Completed"
    Failed = "Failed"


class Runs(Base):
    __tablename__ = "runs"
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    dataset_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("datasets.dataset_id"))
    run_timestamp: Mapped[DateTime] = mapped_column(
        DateTime, default=datetime.datetime.now
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.user_id"))
    algorithm_name: Mapped[str] = mapped_column(String(50))
    parameters: Mapped[dict[str, Any]] = mapped_column(
        MutableDict.as_mutable(JSONB), nullable=True
    )

    status: Mapped[StatusEnum] = mapped_column(Enum(StatusEnum))
