"""
Comprehensive diagnostic script to check if conflict detection is working.

This will:
1. Check the conflict analysis in the database
2. Manually verify conflicts by examining exam assignments
3. Compare what should be detected vs what was detected
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.core.database import SessionLocal
from src.repo.schedule import ScheduleRepo
from src.repo.exam_assignment import ExamAssignmentRepo
from src.repo.conflict_analyses import ConflictAnalysesRepo
from src.repo.course import CourseRepo
from sqlalchemy import desc
from collections import defaultdict

def diagnose():
    """Diagnose conflict detection issues."""
    db = SessionLocal()
    try:
        schedule_repo = ScheduleRepo(db)
        exam_repo = ExamAssignmentRepo(db)
        conflict_repo = ConflictAnalysesRepo(db)
        course_repo = CourseRepo(db)
        
        # Get most recent schedule
        from src.schemas.db import Schedules
        schedules = db.query(Schedules).order_by(desc(Schedules.created_at)).limit(1).all()
        
        if not schedules:
            print("No schedules found")
            return
        
        schedule = schedules[0]
        print(f"\n{'='*70}")
        print(f"DIAGNOSING: {schedule.schedule_name}")
        print(f"Schedule ID: {schedule.schedule_id}")
        print(f"{'='*70}\n")
        
        # Get all exam assignments
        assignments = exam_repo.get_all_for_schedule(schedule.schedule_id)
        print(f"Total exam assignments: {len(assignments)}\n")
        
        # Build student and instructor schedules manually
        # Note: We need enrollment data to check student conflicts properly
        # For now, we'll check instructor conflicts which we can verify
        
        instructor_slots = defaultdict(list)  # (instructor, day, block) -> [crns]
        instructor_days = defaultdict(lambda: defaultdict(list))  # instructor -> day -> [crns]
        
        for assignment in assignments:
            course = assignment.course
            time_slot = assignment.time_slot
            instructor = course.instructor_name
            day = time_slot.day.value
            block = time_slot.slot_label
            crn = course.crn
            
            if instructor:
                instructor_slots[(instructor, day, block)].append(crn)
                instructor_days[instructor][day].append((block, crn))
        
        # Check for instructor double-books
        instructor_double_books = []
        for (instructor, day, block), crns in instructor_slots.items():
            if len(crns) > 1:
                instructor_double_books.append({
                    "instructor": instructor,
                    "day": day,
                    "block": block,
                    "courses": crns
                })
        
        # Check for instructor > max per day (assuming 3)
        instructor_over_limit = []
        for instructor, day_exams in instructor_days.items():
            for day, exams in day_exams.items():
                if len(exams) > 3:
                    instructor_over_limit.append({
                        "instructor": instructor,
                        "day": day,
                        "count": len(exams),
                        "courses": [crn for _, crn in exams]
                    })
        
        print("MANUAL VERIFICATION (from exam assignments):")
        print(f"  Instructor double-books: {len(instructor_double_books)}")
        if instructor_double_books:
            print("  Examples:")
            for db in instructor_double_books[:5]:
                print(f"    - {db['instructor']} on {db['day']}, {db['block']}: {len(db['courses'])} courses")
                print(f"      Courses: {', '.join(str(c) for c in db['courses'][:3])}")
        print()
        
        print(f"  Instructors with >3 exams/day: {len(instructor_over_limit)}")
        if instructor_over_limit:
            print("  Examples:")
            for ol in instructor_over_limit[:5]:
                print(f"    - {ol['instructor']} on {ol['day']}: {ol['count']} exams")
        print()
        
        # Check database conflict analysis
        conflict_analysis = conflict_repo.get_by_schedule_id(schedule.schedule_id)
        
        if conflict_analysis and conflict_analysis.conflicts:
            conflicts_json = conflict_analysis.conflicts
            hard_conflicts = conflicts_json.get("hard_conflicts", {})
            
            db_instructor_double = len(hard_conflicts.get("instructor_double_book", []))
            db_instructor_max = len(hard_conflicts.get("instructor_gt_max_per_day", []))
            
            print("DATABASE CONFLICT ANALYSIS:")
            print(f"  Instructor double-book: {db_instructor_double}")
            print(f"  Instructor > max/day: {db_instructor_max}")
            print()
            
            # Compare
            if len(instructor_double_books) != db_instructor_double:
                print(f"⚠️  MISMATCH: Found {len(instructor_double_books)} instructor double-books manually,")
                print(f"   but database shows {db_instructor_double}")
            else:
                print(f"✅ Instructor double-books match: {db_instructor_double}")
            
            if len(instructor_over_limit) != db_instructor_max:
                print(f"⚠️  MISMATCH: Found {len(instructor_over_limit)} instructor > max/day manually,")
                print(f"   but database shows {db_instructor_max}")
            else:
                print(f"✅ Instructor > max/day match: {db_instructor_max}")
        else:
            print("⚠️  No conflict analysis found in database!")
            print("   This means conflicts were not saved during schedule generation.")
        
        print(f"\n{'='*70}\n")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    diagnose()

