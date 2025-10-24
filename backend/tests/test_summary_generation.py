#!/usr/bin/env python3
"""
Test script to check if the summary generation works
"""
import pandas as pd
import sys
import os
sys.path.append('..')

def test_summary_generation():
    """Test the summary generation function."""
    print("Testing summary generation...")
    
    try:
        # Load the generated schedule
        schedule_df = pd.read_csv('../Data/detailed_exam_schedule.csv')
        print(f"Loaded schedule: {len(schedule_df)} exams")
        
        # Create mock data for testing
        conflicts_df = pd.DataFrame({'Student_ID': [1, 2, 3], 'violation': ['conflict', 'conflict', 'conflict']})
        capacity_violations = pd.DataFrame({'CRN': [1, 2], 'Size': [100, 50], 'Capacity': [80, 40]})
        
        # Mock summary
        summary = {
            'hard_student_conflicts': 0,
            'hard_instructor_conflicts': 0,
            'students_gt2_per_day': 100,
            'students_back_to_back': 50,
            'instructors_back_to_back': 10,
            'large_courses_not_early': 5
        }
        
        # Test the summary generation
        sys.path.append('..')
        from master_validation import generate_algorithm_summary
        result = generate_algorithm_summary(schedule_df, schedule_df, conflicts_df, capacity_violations, summary)
        
        if result:
            print("SUCCESS: Summary generation successful!")
        else:
            print("ERROR: Summary generation failed!")
            
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_summary_generation()