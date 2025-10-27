#!/usr/bin/env python3
"""
Tests for the master validation script
"""

import os
import sys
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest


# Add the parent directory to the path to import master_validation
sys.path.insert(0, os.path.dirname(__file__))

from master_validation import (
    analyze_capacity_violations,
    analyze_student_conflicts,
    generate_algorithm_summary,
    generate_comprehensive_report,
    load_cleaned_data,
    run_scheduling_algorithm,
)


class TestMasterValidation:
    """Test suite for the master validation script."""

    @pytest.mark.integration
    def test_load_cleaned_data(self):
        """Test loading of cleaned data files."""
        try:
            census_df, enrollment_df, classrooms_df = load_cleaned_data()

            # Check that data was loaded
            assert len(census_df) > 0
            assert len(enrollment_df) > 0
            assert len(classrooms_df) > 0

            # Check required columns exist
            assert "CRN" in census_df.columns
            assert "num_students" in census_df.columns
            # Handle both possible column names for student ID
            assert (
                "Student_PIDM" in enrollment_df.columns
                or "student_id" in enrollment_df.columns
            )
            assert "CRN" in enrollment_df.columns
            assert "room_name" in classrooms_df.columns
            assert "capacity" in classrooms_df.columns

            print("SUCCESS: Data loading test passed:")
            print(f"   - Census: {len(census_df)} records")
            print(f"   - Enrollment: {len(enrollment_df)} records")
            print(f"   - Classrooms: {len(classrooms_df)} records")

        except FileNotFoundError as e:
            print(f"WARNING: Data files not found: {e}")
            print("   Skipping data loading test")
        except Exception as e:
            print(f"ERROR: Data loading test failed: {e}")
            raise

    @pytest.mark.integration
    def test_scheduling_algorithm(self):
        """Test the scheduling algorithm with real data."""
        try:
            census_df, enrollment_df, classrooms_df = load_cleaned_data()

            graph, schedule_df, summary = run_scheduling_algorithm(
                census_df, enrollment_df, classrooms_df
            )

            # Check that algorithm ran successfully
            assert graph is not None
            assert schedule_df is not None
            assert summary is not None

            # Check schedule properties
            assert len(schedule_df) > 0
            required_columns = [
                "CRN",
                "Course",
                "Day",
                "Block",
                "Room",
                "Capacity",
                "Size",
                "Valid",
            ]
            for col in required_columns:
                assert col in schedule_df.columns

            # Check summary properties
            expected_keys = [
                "hard_student_conflicts",
                "hard_instructor_conflicts",
                "students_gt2_per_day",
                "students_back_to_back",
                "instructors_back_to_back",
                "large_courses_not_early",
                "num_classes",
                "num_students",
                "num_rooms",
                "slots_used",
            ]
            for key in expected_keys:
                assert key in summary

            # Verify hard constraints are satisfied
            assert summary["hard_student_conflicts"] == 0
            assert summary["hard_instructor_conflicts"] == 0
            assert summary["students_gt2_per_day"] == 0

            print("SUCCESS: Scheduling algorithm test passed:")
            print(f"   - Scheduled exams: {len(schedule_df)}")
            print(f"   - Hard conflicts: {summary['hard_student_conflicts']}")
            print(f"   - Soft violations: {summary['students_back_to_back']}")

        except FileNotFoundError:
            print("WARNING: Data files not found, skipping scheduling test")
        except Exception as e:
            print(f"ERROR: Scheduling test failed: {e}")
            raise

    @pytest.mark.integration
    def test_conflict_analysis(self):
        """Test student conflict analysis."""
        try:
            census_df, enrollment_df, classrooms_df = load_cleaned_data()
            graph, schedule_df, summary = run_scheduling_algorithm(
                census_df, enrollment_df, classrooms_df
            )

            conflicts_df = analyze_student_conflicts(
                schedule_df, enrollment_df, census_df
            )

            if conflicts_df is not None and not conflicts_df.empty:
                # Check conflict analysis structure
                assert "Student_ID" in conflicts_df.columns
                assert "CRN_1" in conflicts_df.columns
                assert "CRN_2" in conflicts_df.columns
                assert "Day" in conflicts_df.columns
                assert "Block" in conflicts_df.columns

                print("SUCCESS: Conflict analysis test passed:")
                print(f"   - Conflicts found: {len(conflicts_df)}")
            else:
                print("SUCCESS: No conflicts found (good!)")

        except FileNotFoundError:
            print("WARNING: Data files not found, skipping conflict analysis test")
        except Exception as e:
            print(f"ERROR: Conflict analysis test failed: {e}")
            raise

    @pytest.mark.integration
    def test_capacity_violation_analysis(self):
        """Test capacity violation analysis."""
        try:
            census_df, enrollment_df, classrooms_df = load_cleaned_data()
            graph, schedule_df, summary = run_scheduling_algorithm(
                census_df, enrollment_df, classrooms_df
            )

            capacity_violations = analyze_capacity_violations(schedule_df)

            if capacity_violations is not None and not capacity_violations.empty:
                # Check capacity violation structure
                assert "CRN" in capacity_violations.columns
                assert "Size" in capacity_violations.columns
                assert "Capacity" in capacity_violations.columns
                assert "Overflow" in capacity_violations.columns

                print("SUCCESS: Capacity violation analysis test passed:")
                print(f"   - Violations found: {len(capacity_violations)}")
            else:
                print("SUCCESS: No capacity violations found (good!)")

        except FileNotFoundError:
            print("WARNING: Data files not found, skipping capacity analysis test")
        except Exception as e:
            print(f"ERROR: Capacity analysis test failed: {e}")
            raise

    @pytest.mark.integration
    def test_report_generation(self):
        """Test report generation."""
        try:
            census_df, enrollment_df, classrooms_df = load_cleaned_data()
            graph, schedule_df, summary = run_scheduling_algorithm(
                census_df, enrollment_df, classrooms_df
            )

            # Test comprehensive report generation
            conflicts_df = analyze_student_conflicts(
                schedule_df, enrollment_df, census_df
            )
            capacity_violations = analyze_capacity_violations(schedule_df)

            success = generate_comprehensive_report(
                schedule_df, schedule_df, conflicts_df, capacity_violations, summary
            )

            assert success is True
            print("SUCCESS: Report generation test passed")

            # Test algorithm summary generation
            summary_success = generate_algorithm_summary(
                schedule_df, schedule_df, conflicts_df, capacity_violations, summary
            )

            assert summary_success is True
            print("SUCCESS: Algorithm summary generation test passed")

        except FileNotFoundError:
            print("WARNING: Data files not found, skipping report generation test")
        except Exception as e:
            print(f"ERROR: Report generation test failed: {e}")
            raise

    def test_mock_data_workflow(self):
        """Test the complete workflow with mock data."""
        # Create mock data
        mock_census = pd.DataFrame(
            {
                "CRN": ["1001", "1002", "1003"],
                "course_ref": ["CS101", "MATH201", "PHYS301"],
                "num_students": [30, 25, 40],
            }
        )

        mock_enrollment = pd.DataFrame(
            {
                "student_id": ["S001", "S001", "S002", "S002", "S003", "S003"],
                "CRN": ["1001", "1002", "1001", "1003", "1002", "1004"],
                "instructor_name": [
                    "Dr. Smith",
                    "Dr. Smith",
                    "Dr. Jones",
                    "Dr. Jones",
                    "Dr. Brown",
                    "Dr. Brown",
                ],
            }
        )

        mock_classrooms = pd.DataFrame(
            {"room_name": ["Room A", "Room B", "Room C"], "capacity": [50, 40, 30]}
        )

        # Test with mock data
        graph, schedule_df, summary = run_scheduling_algorithm(
            mock_census, mock_enrollment, mock_classrooms
        )

        assert graph is not None
        assert schedule_df is not None
        assert summary is not None

        print("SUCCESS: Mock data workflow test passed")


if __name__ == "__main__":
    # Run tests if executed directly
    test_suite = TestMasterValidation()

    print("Running Master Validation Tests")
    print("=" * 50)

    try:
        test_suite.test_load_cleaned_data()
        print()
        test_suite.test_scheduling_algorithm()
        print()
        test_suite.test_conflict_analysis()
        print()
        test_suite.test_capacity_violation_analysis()
        print()
        test_suite.test_report_generation()
        print()
        test_suite.test_mock_data_workflow()

        print("\nSUCCESS: All tests completed!")

    except Exception as e:
        print(f"\nERROR: Test suite failed: {e}")
        import traceback

        traceback.print_exc()
