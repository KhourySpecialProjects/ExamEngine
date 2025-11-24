"""
Quick test to check large course placement in the most recent schedule.
Run this from the backend directory: python quick_test_large_courses.py
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.core.database import SessionLocal
from src.repo.schedule import ScheduleRepo
from src.repo.exam_assignment import ExamAssignmentRepo
from sqlalchemy import desc

def quick_test():
    """Quick test of the most recent schedule."""
    db = SessionLocal()
    try:
        schedule_repo = ScheduleRepo(db)
        exam_repo = ExamAssignmentRepo(db)
        
        # Get most recent schedule
        from src.schemas.db import Schedules
        schedules = db.query(Schedules).order_by(desc(Schedules.created_at)).limit(1).all()
        
        if not schedules:
            print("No schedules found in database")
            return
        
        schedule = schedules[0]
        print(f"\nTesting schedule: {schedule.schedule_name} (ID: {schedule.schedule_id})")
        print(f"Created: {schedule.created_at}\n")
        
        # Get all exam assignments
        assignments = exam_repo.get_all_for_schedule(schedule.schedule_id)
        
        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        day_to_idx = {name: idx for idx, name in enumerate(day_names)}
        
        large_courses = []
        large_late = []
        
        for assignment in assignments:
            course = assignment.course
            time_slot = assignment.time_slot
            size = course.enrollment_count
            
            if size >= 100:
                day_name = time_slot.day.value
                day_idx = day_to_idx.get(day_name, -1)
                
                info = {
                    "crn": course.crn,
                    "course": course.course_subject_code,
                    "size": size,
                    "day": day_name,
                    "day_idx": day_idx,
                    "block": time_slot.slot_label,
                }
                
                large_courses.append(info)
                
                if day_idx > 2:  # Thursday or later
                    large_late.append(info)
        
        print(f"Total courses: {len(assignments)}")
        print(f"Large courses (>=100 students): {len(large_courses)}")
        print(f"  - Early (Mon-Wed): {len(large_courses) - len(large_late)}")
        print(f"  - Late (Thu-Sun): {len(large_late)}\n")
        
        if large_courses:
            print("Large courses by day:")
            for day_idx in range(7):
                day_name = day_names[day_idx]
                courses_this_day = [c for c in large_courses if c['day_idx'] == day_idx]
                if courses_this_day:
                    total_size = sum(c['size'] for c in courses_this_day)
                    print(f"  {day_name}: {len(courses_this_day)} courses, {total_size} total students")
            print()
        
        if large_late:
            print("⚠️  Large courses placed LATE (should be early):")
            for course in sorted(large_late, key=lambda x: x['size'], reverse=True):
                print(f"  - {course['course']} (CRN: {course['crn']}, Size: {course['size']}) on {course['day']}")
            print(f"\n❌ Found {len(large_late)} large courses placed late!")
        else:
            print("✅ All large courses are placed early (Mon-Wed)!")
            if len(large_courses) == 0:
                print("   (No courses with >=100 students found)")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    quick_test()

