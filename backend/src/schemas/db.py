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


class Students(Base):
    __tablename__ = "students"
    student_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    dataset_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("datasets.dataset_id"))
    dataset: Mapped["Datasets"] = relationship(
        "Datasets", back_populates="students", lazy="select"
    )
    conflicts: Mapped[list["Conflicts"]] = relationship(
        "Conflicts", lazy="select", back_populates="student"
    )


class Courses(Base):
    __tablename__ = "courses"
    course_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    course_subject_code: Mapped[str] = mapped_column(String)
    enrollment_count: Mapped[int] = mapped_column(Integer)
    dataset_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("datasets.dataset_id"))
    exam_assignments: Mapped[list["ExamAssignments"]] = relationship(
        "ExamAssignments", lazy="select", back_populates="course"
    )
    dataset: Mapped["Datasets"] = relationship(
        "Datasets", back_populates="courses", lazy="select"
    )


class Conflicts(Base):
    __tablename__ = "conflicts"
    conflict_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        String(50), ForeignKey("students.student_id")
    )
    exam_assignment_ids: Mapped[list[uuid.UUID]] = mapped_column(
        MutableList.as_mutable(JSONB),
        nullable=False,
        default=list,
    )
    conflict_type: Mapped[str] = mapped_column(String)
    schedule_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("schedules.schedule_id"))
    schedule: Mapped["Schedules"] = relationship(
        "Schedules", lazy="select", back_populates="conflicts"
    )

    student: Mapped["Students"] = relationship("Students", lazy="select")


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


class Rooms(Base):
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


class Users(Base):
    __tablename__ = "users"
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    datasets: Mapped[list["Datasets"]] = relationship(
        "Datasets", back_populates="user", lazy="select"
    )
    runs: Mapped[list["Runs"]] = relationship(
        "Runs", back_populates="user", lazy="select"
    )


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
    run: Mapped["Runs"] = relationship(
        "Runs", lazy="select", back_populates="schedules"
    )
    exam_assignments: Mapped[list["ExamAssignments"]] = relationship(
        "ExamAssignments",
        lazy="select",
        back_populates="schedule",
        cascade="all, delete-orphan",
    )
    conflicts: Mapped[list["Conflicts"]] = relationship(
        "Conflicts",
        lazy="select",
        back_populates="schedule",
        cascade="all, delete-orphan",
    )


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
    user: Mapped["Users"] = relationship(
        "Users", back_populates="datasets", lazy="select"
    )
    students: Mapped[list["Students"]] = relationship(
        "Students",
        back_populates="dataset",
        lazy="select",
        cascade="all, delete-orphan",
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
    schedules: Mapped[list["Schedules"]] = relationship(
        "Schedules", lazy="select", back_populates="run"
    )
    dataset: Mapped["Datasets"] = relationship("Datasets", lazy="select")
    user: Mapped["Users"] = relationship("Users", lazy="select")
