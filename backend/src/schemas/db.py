from sqlalchemy import create_engine, Integer, String, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session, relationship

class Base(DeclarativeBase):
    pass

class Enrollments(Base):
    __tablename__ = "enrollments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
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
    crn : Mapped[int] = mapped_column(primary_key=True)
    enrollment_count: Mapped[int] = mapped_column(Integer)
    enrollments: Mapped[list["Enrollments"]] = relationship(back_populates="course")
    
    
class Conflicts(Base):
    __tablename__ = "conflicts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(Integer)
    exam_id: Mapped[int] = mapped_column(Integer)
    conflict_type: Mapped[str] = mapped_column(String)
    
# --- Main logic ---
def main():
    db_url = "postgresql+psycopg2://postgres:postgres@localhost:5432/exam_engine_db"
    engine = create_engine(db_url, echo=True)

    # Create tables
    Base.metadata.create_all(engine)

    # Add a row
    with Session(engine) as session:
        enrollments = Enrollments()
        session.add(Students(student_id=1,enrollments=enrollments))
        session.add(Courses(crn=1234, enrollment_count=25,enrollments=enrollments))
        session.commit()


if __name__ == "__main__":
    main()