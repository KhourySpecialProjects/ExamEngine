"""
Unit tests for merge validation service.
"""

import pytest

from src.domain.models import Course, Room, SchedulingDataset, Student
from src.services.dataset.merge_validator import MergeValidator, MergeValidationResult


@pytest.fixture
def sample_courses():
    """Create sample courses for testing."""
    return {
        "CRN1": Course(
            crn="CRN1",
            course_code="CS 4535",
            enrollment_count=30,
            department="CS",
            examination_term="Fall 2025",
            instructor_names={"Dr. Smith"},
        ),
        "CRN2": Course(
            crn="CRN2",
            course_code="CS 4535",
            enrollment_count=25,
            department="CS",
            examination_term="Fall 2025",
            instructor_names={"Dr. Smith"},
        ),
        "CRN3": Course(
            crn="CRN3",
            course_code="MATH 2000",
            enrollment_count=50,
            department="MATH",
            examination_term="Fall 2025",
            instructor_names={"Dr. Jones"},
        ),
    }


@pytest.fixture
def sample_rooms():
    """Create sample rooms for testing."""
    return [
        Room(name="Room A", capacity=50),
        Room(name="Room B", capacity=100),
        Room(name="Room C", capacity=30),
    ]


@pytest.fixture
def sample_students():
    """Create sample students for testing."""
    return {
        "S001": Student(student_id="S001", enrolled_crns=frozenset(["CRN1", "CRN2"])),
        "S002": Student(student_id="S002", enrolled_crns=frozenset(["CRN1"])),
        "S003": Student(student_id="S003", enrolled_crns=frozenset(["CRN2", "CRN3"])),
    }


@pytest.fixture
def sample_dataset(sample_courses, sample_students, sample_rooms):
    """Create a sample SchedulingDataset."""
    students_by_crn = {
        "CRN1": frozenset(["S001", "S002"]),
        "CRN2": frozenset(["S001", "S003"]),
        "CRN3": frozenset(["S003"]),
    }
    instructors_by_crn = {
        "CRN1": frozenset(["Dr. Smith"]),
        "CRN2": frozenset(["Dr. Smith"]),
        "CRN3": frozenset(["Dr. Jones"]),
    }

    return SchedulingDataset(
        courses=sample_courses,
        students=sample_students,
        rooms=sample_rooms,
        students_by_crn=students_by_crn,
        instructors_by_crn=instructors_by_crn,
    )


class TestMergeValidator:
    """Tests for MergeValidator service."""

    def test_validate_merge_valid(self, sample_dataset):
        """Test validation of a valid merge (fits in room)."""
        validator = MergeValidator(sample_dataset)
        result = validator.validate_merge(["CRN1", "CRN2"])

        assert isinstance(result, MergeValidationResult)
        assert result.is_valid is True
        assert result.total_enrollment == 55  # 30 + 25
        assert result.max_room_capacity == 100
        assert result.crns == ["CRN1", "CRN2"]
        assert result.warning_message is None
        assert result.can_proceed is True

    def test_validate_merge_exceeds_capacity(self, sample_dataset):
        """Test validation when merge exceeds room capacity."""
        # Create a course that's too large
        large_course = Course(
            crn="CRN4",
            course_code="CS 9999",
            enrollment_count=150,
            department="CS",
            examination_term="Fall 2025",
            instructor_names={"Dr. Large"},
        )
        sample_dataset.courses["CRN4"] = large_course
        sample_dataset.students_by_crn["CRN4"] = frozenset()

        validator = MergeValidator(sample_dataset)
        result = validator.validate_merge(["CRN3", "CRN4"])

        assert result.is_valid is False
        assert result.total_enrollment == 200  # 50 + 150
        assert result.max_room_capacity == 100
        assert result.warning_message is not None
        assert "200" in result.warning_message
        assert "100" in result.warning_message
        assert result.can_proceed is True  # User can still proceed

    def test_validate_merge_empty_list(self, sample_dataset):
        """Test validation with empty CRN list."""
        validator = MergeValidator(sample_dataset)
        with pytest.raises(ValueError, match="Cannot merge empty list"):
            validator.validate_merge([])

    def test_validate_merge_single_crn(self, sample_dataset):
        """Test validation with only one CRN."""
        validator = MergeValidator(sample_dataset)
        with pytest.raises(ValueError, match="Need at least 2 CRNs"):
            validator.validate_merge(["CRN1"])

    def test_validate_merge_invalid_crn(self, sample_dataset):
        """Test validation with non-existent CRN."""
        validator = MergeValidator(sample_dataset)
        with pytest.raises(ValueError, match="CRNs not found"):
            validator.validate_merge(["CRN1", "INVALID_CRN"])

    def test_validate_multiple_merges(self, sample_dataset):
        """Test validating multiple merge groups at once."""
        validator = MergeValidator(sample_dataset)
        merges = {
            "merge_1": ["CRN1", "CRN2"],
            "merge_2": ["CRN3"],
        }

        results = validator.validate_multiple_merges(merges)

        assert "merge_1" in results
        assert "merge_2" in results
        assert results["merge_1"].is_valid is True
        # merge_2 should have error (only 1 CRN)
        assert results["merge_2"].is_valid is False
        assert "Need at least 2 CRNs" in results["merge_2"].warning_message

    def test_validation_result_to_dict(self, sample_dataset):
        """Test that validation result can be converted to dict."""
        validator = MergeValidator(sample_dataset)
        result = validator.validate_merge(["CRN1", "CRN2"])

        result_dict = result.to_dict()

        assert isinstance(result_dict, dict)
        assert "is_valid" in result_dict
        assert "total_enrollment" in result_dict
        assert "max_room_capacity" in result_dict
        assert "crns" in result_dict
        assert "warning_message" in result_dict
        assert "can_proceed" in result_dict
        assert "suggested_action" in result_dict

    def test_merge_with_no_rooms(self):
        """Test validation when dataset has no rooms."""
        courses = {
            "CRN1": Course(
                crn="CRN1",
                course_code="CS 101",
                enrollment_count=30,
                department="CS",
                examination_term="Fall 2025",
            ),
        }
        dataset = SchedulingDataset(
            courses=courses,
            students={},
            rooms=[],  # No rooms
            students_by_crn={"CRN1": frozenset()},
            instructors_by_crn={"CRN1": frozenset()},
        )

        validator = MergeValidator(dataset)
        # Should handle gracefully - max capacity would be 0
        result = validator.validate_merge(["CRN1", "CRN1"])  # Same CRN twice for test

        # This is an edge case - we'd need 2 different CRNs
        # But the point is it should handle empty rooms list
        assert result.max_room_capacity == 0

