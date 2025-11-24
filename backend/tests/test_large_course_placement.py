"""
Test script to verify large course early placement is working correctly.

This script:
1. Checks if large courses (>=100 students) are being placed early (Mon-Wed)
2. Reports any large courses placed late (Thu-Sun)
3. Shows statistics about course sizes and placements
"""

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.core.database import SessionLocal
from src.repo.schedule import ScheduleRepo
from src.repo.exam_assignment import ExamAssignmentRepo
from src.repo.course import CourseRepo
from src.repo.time_slot import TimeSlotRepo
from uuid import UUID

def test_large_course_placement(schedule_id: str):
    """Test if large courses are placed early in the week."""
    db = SessionLocal()
    try:
        schedule_repo = ScheduleRepo(db)
        exam_repo = ExamAssignmentRepo(db)
        course_repo = CourseRepo(db)
        time_slot_repo = TimeSlotRepo(db)
        
        schedule_uuid = UUID(schedule_id)
        schedule = schedule_repo.get_by_id(schedule_uuid)
        
        if not schedule:
            print(f"Schedule {schedule_id} not found")
            return
        
        print(f"\n{'='*60}")
        print(f"Testing Large Course Placement for Schedule: {schedule.schedule_name}")
        print(f"{'='*60}\n")
        
        # Get all exam assignments for this schedule
        assignments = exam_repo.get_all_for_schedule(schedule_uuid)
        
        # Day mapping: 0=Monday, 1=Tuesday, 2=Wednesday, 3=Thursday, 4=Friday, 5=Saturday, 6=Sunday
        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        
        # Analyze course placements
        large_courses = []  # Courses with >=100 students
        large_courses_early = []  # Large courses on Mon-Wed (days 0-2)
        large_courses_late = []  # Large courses on Thu-Sun (days 3-6)
        
        for assignment in assignments:
            course = assignment.course
            time_slot = assignment.time_slot
            size = course.enrollment_count
            
            if size >= 100:
                day_idx = None
                day_name = time_slot.day.value
                for i, name in enumerate(day_names):
                    if name == day_name:
                        day_idx = i
                        break
                
                course_info = {
                    "crn": course.crn,
                    "course": course.course_subject_code,
                    "size": size,
                    "day": day_name,
                    "day_idx": day_idx,
                    "block": time_slot.slot_label,
                }
                
                large_courses.append(course_info)
                
                if day_idx is not None:
                    if day_idx <= 2:  # Mon-Wed (early)
                        large_courses_early.append(course_info)
                    else:  # Thu-Sun (late)
                        large_courses_late.append(course_info)
        
        # Print results
        print(f"Total courses scheduled: {len(assignments)}")
        print(f"Large courses (>=100 students): {len(large_courses)}")
        print(f"  - Placed early (Mon-Wed): {len(large_courses_early)}")
        print(f"  - Placed late (Thu-Sun): {len(large_courses_late)}")
        print()
        
        if large_courses:
            print(f"Large Course Details:")
            print(f"{'CRN':<10} {'Course':<15} {'Size':<8} {'Day':<12} {'Block':<20}")
            print("-" * 70)
            for course in sorted(large_courses, key=lambda x: x['size'], reverse=True):
                status = "✓ EARLY" if course in large_courses_early else "✗ LATE"
                print(f"{course['crn']:<10} {course['course']:<15} {course['size']:<8} {course['day']:<12} {course['block']:<20} {status}")
            print()
        
        if large_courses_late:
            print(f"\n⚠️  WARNING: {len(large_courses_late)} large courses placed LATE (Thu-Sun):")
            for course in large_courses_late:
                print(f"  - {course['course']} (CRN: {course['crn']}, Size: {course['size']}) on {course['day']}")
            print()
        else:
            print("✓ All large courses are placed early (Mon-Wed)!\n")
        
        # Check if prioritize_large_courses was used
        # This would be in the run parameters, but we can infer from placement
        if large_courses:
            avg_size_early = sum(c['size'] for c in large_courses_early) / len(large_courses_early) if large_courses_early else 0
            avg_size_late = sum(c['size'] for c in large_courses_late) / len(large_courses_late) if large_courses_late else 0
            
            print(f"Average size of large courses placed early: {avg_size_early:.1f}")
            if large_courses_late:
                print(f"Average size of large courses placed late: {avg_size_late:.1f}")
            print()
        
        # Summary
        if len(large_courses_late) == 0:
            print("✅ TEST PASSED: All large courses are placed early!")
        else:
            print(f"❌ TEST FAILED: {len(large_courses_late)} large courses are placed late")
            print("   This suggests the large course early placement logic may not be working correctly.")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_large_course_placement.py <schedule_id>")
        print("\nExample:")
        print("  python test_large_course_placement.py 123e4567-e89b-12d3-a456-426614174000")
        sys.exit(1)
    
    schedule_id = sys.argv[1]
    test_large_course_placement(schedule_id)

