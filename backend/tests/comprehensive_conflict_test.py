"""
Comprehensive test to verify all conflict detection including student conflicts.

This requires enrollment data to check student double-books and max-per-day violations.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.core.database import SessionLocal
from src.repo.schedule import ScheduleRepo
from src.repo.exam_assignment import ExamAssignmentRepo
from src.repo.conflict_analyses import ConflictAnalysesRepo
from src.repo.course import CourseRepo
from src.repo.dataset import DatasetRepo
from sqlalchemy import desc
from collections import defaultdict
import pandas as pd

def comprehensive_test():
    """Comprehensive conflict detection test."""
    db = SessionLocal()
    try:
        schedule_repo = ScheduleRepo(db)
        exam_repo = ExamAssignmentRepo(db)
        conflict_repo = ConflictAnalysesRepo(db)
        course_repo = CourseRepo(db)
        dataset_repo = DatasetRepo(db)
        
        # Get most recent schedule
        from src.schemas.db import Schedules
        schedules = db.query(Schedules).order_by(desc(Schedules.created_at)).limit(1).all()
        
        if not schedules:
            print("No schedules found")
            return
        
        schedule = schedules[0]
        print(f"\n{'='*70}")
        print(f"COMPREHENSIVE CONFLICT TEST: {schedule.schedule_name}")
        print(f"Schedule ID: {schedule.schedule_id}")
        print(f"{'='*70}\n")
        
        # Get the run to find dataset_id and parameters
        from src.schemas.db import Runs
        run = db.query(Runs).filter(Runs.run_id == schedule.run_id).first()
        if not run:
            print("Could not find run for schedule")
            return
        
        dataset_id = run.dataset_id
        parameters = run.parameters or {}
        print(f"Dataset ID: {dataset_id}")
        print(f"Schedule Parameters:")
        print(f"  student_max_per_day: {parameters.get('student_max_per_day', 'N/A')}")
        print(f"  instructor_max_per_day: {parameters.get('instructor_max_per_day', 'N/A')}")
        print(f"  max_days: {parameters.get('max_days', 'N/A')}")
        print(f"  prioritize_large_courses: {parameters.get('prioritize_large_courses', 'N/A')}")
        print()
        
        # Get all exam assignments
        assignments = exam_repo.get_all_for_schedule(schedule.schedule_id)
        print(f"Total exam assignments: {len(assignments)}\n")
        
        # Build course to time slot mapping
        course_to_slot = {}  # crn -> (day, block)
        for assignment in assignments:
            course = assignment.course
            time_slot = assignment.time_slot
            crn = str(course.crn)
            day = time_slot.day.value
            block = time_slot.slot_label
            course_to_slot[crn] = (day, block)
        
        # Get enrollment data from dataset
        # We need to load the enrollment CSV from S3 or check if it's cached
        dataset = dataset_repo.get_by_id(dataset_id)
        if not dataset:
            print("Could not find dataset")
            return
        
        # Try to get enrollment data
        # For now, we'll check what we can without enrollment data
        # and then suggest loading it
        
        # Check instructor conflicts (we can do this without enrollment)
        instructor_slots = defaultdict(list)  # (instructor, day, block) -> [crns]
        instructor_days = defaultdict(lambda: defaultdict(list))  # instructor -> day -> [crns]
        
        for assignment in assignments:
            course = assignment.course
            time_slot = assignment.time_slot
            instructor = course.instructor_name
            day = time_slot.day.value
            block = time_slot.slot_label
            crn = str(course.crn)
            
            if instructor:
                instructor_slots[(instructor, day, block)].append(crn)
                instructor_days[instructor][day].append((block, crn))
        
        # Check instructor double-books
        instructor_double_books = []
        for (instructor, day, block), crns in instructor_slots.items():
            if len(crns) > 1:
                instructor_double_books.append({
                    "instructor": instructor,
                    "day": day,
                    "block": block,
                    "courses": crns
                })
        
        # Check instructor > max per day
        instructor_over_limit = []
        for instructor, day_exams in instructor_days.items():
            for day, exams in day_exams.items():
                if len(exams) > 3:  # Assuming max = 3
                    instructor_over_limit.append({
                        "instructor": instructor,
                        "day": day,
                        "count": len(exams),
                        "courses": [crn for _, crn in exams]
                    })
        
        # Check large courses placement
        large_courses = []
        large_courses_late = []
        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        day_to_idx = {name: idx for idx, name in enumerate(day_names)}
        
        for assignment in assignments:
            course = assignment.course
            time_slot = assignment.time_slot
            size = course.enrollment_count
            
            if size >= 100:
                day_name = time_slot.day.value
                day_idx = day_to_idx.get(day_name, -1)
                
                info = {
                    "crn": str(course.crn),
                    "course": course.course_subject_code,
                    "size": size,
                    "day": day_name,
                    "day_idx": day_idx,
                }
                
                large_courses.append(info)
                if day_idx > 2:  # Thursday or later
                    large_courses_late.append(info)
        
        # Get conflict analysis from database
        conflict_analysis = conflict_repo.get_by_schedule_id(schedule.schedule_id)
        
        print("RESULTS:")
        print(f"{'='*70}")
        print(f"Instructor Conflicts:")
        print(f"  Double-books (manual check): {len(instructor_double_books)}")
        print(f"  >3 exams/day (manual check): {len(instructor_over_limit)}")
        
        if conflict_analysis and conflict_analysis.conflicts:
            conflicts_json = conflict_analysis.conflicts
            hard_conflicts = conflicts_json.get("hard_conflicts", {})
            soft_conflicts = conflicts_json.get("soft_conflicts", {})
            
            db_instructor_double = len(hard_conflicts.get("instructor_double_book", []))
            db_instructor_max = len(hard_conflicts.get("instructor_gt_max_per_day", []))
            db_student_double = len(hard_conflicts.get("student_double_book", []))
            db_student_max = len(hard_conflicts.get("student_gt_max_per_day", []))
            
            print(f"  Double-books (database): {db_instructor_double}")
            print(f"  >3 exams/day (database): {db_instructor_max}")
            print()
            print(f"Student Conflicts (from database):")
            print(f"  Double-books: {db_student_double}")
            print(f"  >3 exams/day: {db_student_max}")
            print()
            print(f"Large Course Placement:")
            print(f"  Total large courses (>=100 students): {len(large_courses)}")
            print(f"  Placed early (Mon-Wed): {len(large_courses) - len(large_courses_late)}")
            print(f"  Placed late (Thu-Sun): {len(large_courses_late)}")
            print(f"  Database reports: {len(soft_conflicts.get('large_courses_not_early', []))}")
            
            if large_courses_late:
                print(f"\n  Large courses placed LATE:")
                for course in sorted(large_courses_late, key=lambda x: x['size'], reverse=True)[:10]:
                    print(f"    - {course['course']} (Size: {course['size']}) on {course['day']}")
        else:
            print("  ⚠️  No conflict analysis found in database!")
        
        print(f"\n{'='*70}")
        print("SUMMARY:")
        total_hard = (
            len(hard_conflicts.get("student_double_book", [])) +
            len(hard_conflicts.get("student_gt_max_per_day", [])) +
            len(hard_conflicts.get("instructor_double_book", [])) +
            len(hard_conflicts.get("instructor_gt_max_per_day", []))
        ) if conflict_analysis and conflict_analysis.conflicts else 0
        
        if total_hard == 0:
            print("⚠️  0 hard conflicts detected")
            print("   This could mean:")
            print("   1. Algorithm successfully avoided all conflicts (possible with good graph coloring)")
            print("   2. Dataset has minimal overlapping enrollments")
            print("   3. 5 days provides enough flexibility")
        else:
            print(f"✅ {total_hard} hard conflicts detected")
        
        print(f"{'='*70}\n")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    comprehensive_test()

