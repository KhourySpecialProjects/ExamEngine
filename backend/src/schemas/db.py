from sqlalchemy import create_engine, Integer, String, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session, relationship
import uuid

class Base(DeclarativeBase):
    pass

class Enrollments(Base):
    __tablename__ = "enrollments"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    crn: Mapped[int] = mapped_column(ForeignKey("courses.crn"))
    student_id: Mapped[int] = mapped_column(ForeignKey("students.student_id")) #fk constraint
    
    course: Mapped["Courses"] = relationship(back_populates="enrollments")
    student: Mapped["Students"] = relationship(back_populates="enrollments") #allows us to do enrollment.student.[field]
    
    
class Students(Base):
    __tablename__ = "students"
    student_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    enrollments: Mapped[list["Enrollments"]] = relationship(back_populates="student")
    
class Courses(Base):
    __tablename__ = "courses" 
    crn: Mapped[int] = mapped_column(Integer, primary_key=True)
    enrollment_count: Mapped[int] = mapped_column(Integer)
    enrollments: Mapped[list["Enrollments"]] = relationship(back_populates="course")
    
class Conflicts(Base):
    __tablename__ = "conflicts"   
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid = True), primary_key=True, default=uuid.uuid4)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.student_id"))
    exam_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid= True))
    conflict_type: Mapped[str] = mapped_column(String)
    
# --- Main logic ---
def main():
    db_url = "postgresql+psycopg2://postgres:postgres@localhost:5432/exam_engine_db"
    engine = create_engine(db_url, echo=True)
    
    Base.metadata.create_all(engine)
    
    with Session(engine) as session:
        # First create student and course
        student = Students(student_id=1)
        course = Courses(crn=1234, enrollment_count=25)
        
        # Then create enrollment linking them
        enrollment = Enrollments(student=student, course=course)
        
        # Add all to session
        session.add(student)
        session.add(course)
        session.add(enrollment)
        session.commit()

if __name__ == "__main__":  
    main()
