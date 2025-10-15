from sqlalchemy import create_engine, Integer, String, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session
from uuid import UUID
import uuid
from uuid import UUID

import uuid
from sqlalchemy.dialects.postgresql import UUID  
from sqlalchemy.orm import Mapped, mapped_column, DeclarativeBase
from sqlalchemy import String, Integer
import enum
import uuid
import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    Enum, ForeignKey, Integer, String,  Time, DateTime,
    create_engine
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.mutable import MutableDict, MutableList
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session


class Base(DeclarativeBase):
    pass

    
class Students(Base):
    __tablename__ = "students"
    student_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dataset_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("datasets.dataset_id"))
    
class Courses(Base):
    __tablename__ = "courses" 
    course_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    course_subject_code: Mapped[str] = mapped_column(String)
    enrollment_count: Mapped[int] = mapped_column(Integer)
    dataset_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("datasets.dataset_id"))
    
    
class Conflicts(Base):
    __tablename__ = "conflicts"   
    conflict_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("students.student_id"))
    exam_assignment_ids: Mapped[list[uuid.UUID]] = mapped_column(MutableList.as_mutable(JSONB), nullable=False, default=list,)
    conflict_type: Mapped[str] = mapped_column(String)
    schedule_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("schedules.schedule_id"))

class ExamAssignments(Base):
    __tablename__ = "exam_assignments"
    exam_assignment_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    course_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("courses.course_id"))
    time_slot_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("time_slots.time_slot_id"))
    room_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("rooms.room_id"))
    schedule_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("schedules.schedule_id"))

class Rooms(Base):
    __tablename__ = "rooms"
    room_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
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
    time_slot_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slot_label: Mapped[str] = mapped_column(String(10))
    day: Mapped[DayEnum] = mapped_column(Enum(DayEnum))
    start_time: Mapped[datetime.time] = mapped_column(Time)
    end_time: Mapped[datetime.time] = mapped_column(Time)
    dataset_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("datasets.dataset_id"))
    
class Users(Base):
    __tablename__ = "users"
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(25), nullable=False)
    email: Mapped[str] = mapped_column(String(25), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(50), nullable=False)

class Schedules(Base):
    __tablename__ = "schedules"
    schedule_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    schedule_name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    created_at: Mapped[datetime.time] = mapped_column(DateTime, default=datetime.datetime.utcnow)
    run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("runs.run_id"))
    
class Datasets(Base):
    __tablename__ = "datasets"
    dataset_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    semester: Mapped[str] = mapped_column(String(10))
    upload_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.user_id"))
    file_paths: Mapped[list[str]] = mapped_column(MutableList.as_mutable(JSONB), nullable=False)

class StatusEnum(enum.Enum):
    Running = "Running"
    Completed = "Completed"
    Failed = "Failed"

class Runs(Base):
    __tablename__ = "runs"
    run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dataset_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("datasets.dataset_id"))
    run_timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.user_id"))
    algorithm_name: Mapped[str] = mapped_column(String(50))
    parameters: Mapped[dict[str, Any]] = mapped_column(MutableDict.as_mutable(JSONB), nullable=True)
    
    status: Mapped[StatusEnum] = mapped_column(Enum(StatusEnum)) 

# --- Main logic ---
def main():
    db_url = "postgresql+psycopg2://postgres:postgres@localhost:5432/exam_engine_db"
    engine = create_engine(db_url, echo=True)
    
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    
    with Session(engine) as session:
        user = Users(name="Test User2", email="test@example2.com", password_hash="hashed_password2")
        session.add(user)
        session.flush()  
        
        dataset = Datasets(semester="Fall 20242", user_id=user.user_id, file_paths=["path12.csv", "path22.csv"])
        session.add(dataset)
        session.flush()  
        
        student = Students(dataset_id=dataset.dataset_id)
        course = Courses(course_subject_code="CS1012", enrollment_count=25, dataset_id=dataset.dataset_id)
        
        session.add(student)
        session.add(course)
        session.commit()
        
        print("Successfully created database with test data!")

if __name__ == "__main__":  
    main()
