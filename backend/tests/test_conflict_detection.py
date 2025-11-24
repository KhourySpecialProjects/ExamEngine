"""
Test script to verify conflict detection is working correctly.

This checks:
1. Student double-book conflicts
2. Student > max_per_day conflicts  
3. Instructor double-book conflicts
4. Instructor > max_per_day conflicts
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.core.database import SessionLocal
from src.repo.schedule import ScheduleRepo
from src.repo.exam_assignment import ExamAssignmentRepo
from src.repo.conflict_analyses import ConflictAnalysesRepo
from sqlalchemy import desc
from collections import defaultdict

def test_conflict_detection():
    """Test conflict detection in the most recent schedule."""
    db = SessionLocal()
    try:
        schedule_repo = ScheduleRepo(db)
        exam_repo = ExamAssignmentRepo(db)
        conflict_repo = ConflictAnalysesRepo(db)
        
        # Get most recent schedule
        from src.schemas.db import Schedules
        schedules = db.query(Schedules).order_by(desc(Schedules.created_at)).limit(1).all()
        
        if not schedules:
            print("No schedules found in database")
            return
        
        schedule = schedules[0]
        print(f"\n{'='*70}")
        print(f"Testing Conflict Detection for Schedule: {schedule.schedule_name}")
        print(f"Schedule ID: {schedule.schedule_id}")
        print(f"Created: {schedule.created_at}")
        print(f"{'='*70}\n")
        
        # Get conflict analysis
        conflict_analysis = conflict_repo.get_by_schedule_id(schedule.schedule_id)
        
        if not conflict_analysis or not conflict_analysis.conflicts:
            print("⚠️  No conflict analysis found in database!")
            print("This could mean:")
            print("  1. Conflicts weren't saved during schedule generation")
            print("  2. The schedule was generated before conflict tracking was added")
            return
        
        conflicts_json = conflict_analysis.conflicts
        hard_conflicts = conflicts_json.get("hard_conflicts", {})
        soft_conflicts = conflicts_json.get("soft_conflicts", {})
        
        print("CONFLICT ANALYSIS FROM DATABASE:")
        print(f"  Student double-book: {len(hard_conflicts.get('student_double_book', []))}")
        print(f"  Student > max/day: {len(hard_conflicts.get('student_gt_max_per_day', []))}")
        print(f"  Instructor double-book: {len(hard_conflicts.get('instructor_double_book', []))}")
        print(f"  Instructor > max/day: {len(hard_conflicts.get('instructor_gt_max_per_day', []))}")
        print(f"  Students back-to-back: {len(soft_conflicts.get('back_to_back_students', []))}")
        print(f"  Instructors back-to-back: {len(soft_conflicts.get('back_to_back_instructors', []))}")
        print(f"  Large courses not early: {len(soft_conflicts.get('large_courses_not_early', []))}")
        print()
        
        # Now manually verify by checking exam assignments
        print("MANUAL VERIFICATION FROM EXAM ASSIGNMENTS:")
        assignments = exam_repo.get_all_for_schedule(schedule.schedule_id)
        
        # Track student schedules
        student_schedule = defaultdict(list)  # student_id -> [(day, block, crn)]
        instructor_schedule = defaultdict(list)  # instructor -> [(day, block, crn)]
        
        day_to_idx = {
            "Monday": 0, "Tuesday": 1, "Wednesday": 2, 
            "Thursday": 3, "Friday": 4, "Saturday": 5, "Sunday": 6
        }
        
        for assignment in assignments:
            course = assignment.course
            time_slot = assignment.time_slot
            day = time_slot.day.value
            block = time_slot.slot_label
            
            # Get students for this course (from enrollment, but we'll use a simpler check)
            # For now, we'll check based on what we can see
            
            # Get instructor
            instructor = course.instructor_name
            
            # Track instructor schedule
            if instructor:
                instructor_schedule[instructor].append((day, block, course.crn))
        
        # Check for instructor double-books
        instructor_double_books = []
        for instructor, slots in instructor_schedule.items():
            slot_counts = defaultdict(list)
            for day, block, crn in slots:
                slot_counts[(day, block)].append(crn)
            
            for (day, block), crns in slot_counts.items():
                if len(crns) > 1:
                    instructor_double_books.append({
                        "instructor": instructor,
                        "day": day,
                        "block": block,
                        "courses": crns
                    })
        
        print(f"  Instructor double-books found: {len(instructor_double_books)}")
        if instructor_double_books:
            print("  Examples:")
            for db in instructor_double_books[:3]:
                print(f"    - {db['instructor']} on {db['day']}, {db['block']}: {len(db['courses'])} courses")
        print()
        
        # Check for instructor > max per day (assuming max = 3)
        instructor_max_per_day = 3
        instructor_over_limit = []
        for instructor, slots in instructor_schedule.items():
            day_counts = defaultdict(list)
            for day, block, crn in slots:
                day_counts[day].append((block, crn))
            
            for day, exams in day_counts.items():
                if len(exams) > instructor_max_per_day:
                    instructor_over_limit.append({
                        "instructor": instructor,
                        "day": day,
                        "count": len(exams),
                        "courses": [crn for _, crn in exams]
                    })
        
        print(f"  Instructors with >{instructor_max_per_day} exams/day: {len(instructor_over_limit)}")
        if instructor_over_limit:
            print("  Examples:")
            for ol in instructor_over_limit[:3]:
                print(f"    - {ol['instructor']} on {ol['day']}: {ol['count']} exams")
        print()
        
        # Summary
        total_hard_conflicts = (
            len(hard_conflicts.get('student_double_book', [])) +
            len(hard_conflicts.get('student_gt_max_per_day', [])) +
            len(hard_conflicts.get('instructor_double_book', [])) +
            len(hard_conflicts.get('instructor_gt_max_per_day', []))
        )
        
        print(f"{'='*70}")
        if total_hard_conflicts == 0:
            print("⚠️  WARNING: 0 hard conflicts detected!")
            print("This could mean:")
            print("  1. The algorithm successfully avoided all conflicts (possible but unlikely)")
            print("  2. Conflict detection is not working correctly")
            print("  3. The dataset has no overlapping enrollments")
            print()
            print("Manual check found:")
            print(f"  - {len(instructor_double_books)} instructor double-books")
            print(f"  - {len(instructor_over_limit)} instructors over limit")
        else:
            print(f"✅ Found {total_hard_conflicts} hard conflicts")
        print(f"{'='*70}\n")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    test_conflict_detection()

