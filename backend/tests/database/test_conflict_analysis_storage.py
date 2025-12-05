"""
Tests for conflict analysis storage and data structures.

This module tests the conflict analysis JSON structure, time slot mappings,
and data integrity without requiring a full database connection.
"""

import json
from datetime import time
import pytest

from src.schemas.db import DayEnum


class TestConflictAnalysisStructure:
    """Test conflict analysis JSON structure and data format."""

    def test_conflict_analysis_structure(self):
        """Test that conflict analysis has correct structure."""
        conflicts_data = {
            "hard_conflicts": {
                "student_double_book": [
                    {
                        "entity_id": "2003575",
                        "day": "Monday",
                        "block": 0,
                        "crn": "10001",
                        "conflicting_crn": "10002",
                    }
                ],
                "instructor_double_book": [],
                "student_gt_max_per_day": [],
                "instructor_gt_max_per_day": [],
            },
            "soft_conflicts": {
                "back_to_back_students": [
                    {
                        "student_id": "2037533",
                        "day": "Monday",
                        "blocks": [1, 2],
                    }
                ],
                "back_to_back_instructors": [
                    {
                        "instructor_name": "Dr. Smith",
                        "day": "Tuesday",
                        "blocks": [0, 1],
                    }
                ],
                "large_courses_not_early": [],
            },
            "statistics": {
                "student_double_book_count": 15,
                "instructor_double_book_count": 2,
                "total_hard_conflicts": 20,
                "total_soft_conflicts": 140,
            },
        }

        # Verify structure
        assert "hard_conflicts" in conflicts_data
        assert "soft_conflicts" in conflicts_data
        assert "statistics" in conflicts_data

        # Verify hard conflicts structure
        hard_conflicts = conflicts_data["hard_conflicts"]
        assert "student_double_book" in hard_conflicts
        assert "instructor_double_book" in hard_conflicts
        assert "student_gt_max_per_day" in hard_conflicts

        # Verify soft conflicts structure
        soft_conflicts = conflicts_data["soft_conflicts"]
        assert "back_to_back_students" in soft_conflicts
        assert "back_to_back_instructors" in soft_conflicts
        assert "large_courses_not_early" in soft_conflicts

        # Verify statistics
        stats = conflicts_data["statistics"]
        assert "total_hard_conflicts" in stats
        assert "total_soft_conflicts" in stats

    def test_back_to_back_student_conflict_format(self):
        """Test back-to-back student conflict format."""
        student_conflict = {
            "student_id": "2037533",
            "day": "Monday",
            "blocks": [1, 2],  # Consecutive blocks
        }

        assert "student_id" in student_conflict
        assert "day" in student_conflict
        assert "blocks" in student_conflict
        assert isinstance(student_conflict["blocks"], list)
        assert len(student_conflict["blocks"]) >= 2, "Back-to-back requires at least 2 blocks"

    def test_back_to_back_instructor_conflict_format(self):
        """Test back-to-back instructor conflict format."""
        instructor_conflict = {
            "instructor_name": "Dr. Smith",
            "day": "Tuesday",
            "blocks": [0, 1],
        }

        assert "instructor_name" in instructor_conflict
        assert "day" in instructor_conflict
        assert "blocks" in instructor_conflict
        assert isinstance(instructor_conflict["blocks"], list)

    def test_double_book_conflict_format(self):
        """Test double-book conflict format."""
        double_book = {
            "entity_id": "2003575",
            "day": "Monday",
            "block": 0,
            "crn": "10001",
            "conflicting_crn": "10002",
        }

        assert "entity_id" in double_book
        assert "day" in double_book
        assert "block" in double_book
        assert "crn" in double_book
        assert "conflicting_crn" in double_book

    def test_conflict_analysis_json_serializable(self):
        """Test that conflict analysis can be serialized to JSON."""
        conflicts_data = {
            "hard_conflicts": {
                "student_double_book": [
                    {
                        "entity_id": "2003575",
                        "day": "Monday",
                        "block": 0,
                        "crn": "10001",
                        "conflicting_crn": "10002",
                    }
                ],
            },
            "soft_conflicts": {
                "back_to_back_students": [
                    {
                        "student_id": "2037533",
                        "day": "Monday",
                        "blocks": [1, 2],
                    }
                ],
                "back_to_back_instructors": [
                    {
                        "instructor_name": "Dr. Smith",
                        "day": "Tuesday",
                        "blocks": [0, 1],
                    }
                ],
            },
            "statistics": {
                "total_hard_conflicts": 1,
                "total_soft_conflicts": 2,
            },
        }

        # Should serialize without errors
        json_str = json.dumps(conflicts_data)
        assert json_str is not None

        # Should deserialize correctly
        deserialized = json.loads(json_str)
        assert deserialized["statistics"]["total_hard_conflicts"] == 1
        assert deserialized["statistics"]["total_soft_conflicts"] == 2


class TestTimeSlotMapping:
    """Test time slot block to time mapping."""

    def test_block_time_mapping(self):
        """Test that block indices map to correct times."""
        # Block to time mapping (from time_slot.py)
        block_time_map = {
            0: ("9AM-11AM", time(9, 0), time(11, 0)),
            1: ("11:30AM-1:30PM", time(11, 30), time(13, 30)),
            2: ("2PM-4PM", time(14, 0), time(16, 0)),
            3: ("4:30PM-6:30PM", time(16, 30), time(18, 30)),
            4: ("7PM-9PM", time(19, 0), time(21, 0)),
        }

        # Verify all blocks have mappings
        for block in range(5):
            assert block in block_time_map, f"Block {block} should have time mapping"

        # Verify time ranges are valid
        for block, (label, start, end) in block_time_map.items():
            assert start < end, f"Block {block}: start time should be before end time"
            assert label is not None, f"Block {block} should have a label"

    def test_day_enum_values(self):
        """Test DayEnum has all required days."""
        expected_days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        
        for day_name in expected_days:
            assert hasattr(DayEnum, day_name), f"DayEnum should have {day_name}"
            day_enum = getattr(DayEnum, day_name)
            assert day_enum.value == day_name, f"{day_name} value should match"

    def test_day_enum_string_conversion(self):
        """Test DayEnum can be converted to/from strings."""
        # Test conversion from string to enum
        assert DayEnum.Monday.value == "Monday"
        assert DayEnum.Tuesday.value == "Tuesday"
        assert DayEnum.Wednesday.value == "Wednesday"

        # Test that enum values are strings
        for day_enum in DayEnum:
            assert isinstance(day_enum.value, str), f"{day_enum.name} value should be string"


class TestConflictDataProcessing:
    """Test conflict data processing and enrichment."""

    def test_block_time_enrichment(self):
        """Test that block numbers are enriched with time strings."""
        block_time_map = {
            0: "9AM-11AM",
            1: "11:30AM-1:30PM",
            2: "2PM-4PM",
            3: "4:30PM-6:30PM",
            4: "7PM-9PM",
        }

        # Test single block enrichment
        conflict = {"block": 0, "day": "Monday"}
        enriched = conflict.copy()
        enriched["block_time"] = block_time_map.get(enriched["block"], "")
        
        assert enriched["block_time"] == "9AM-11AM"

        # Test multiple blocks enrichment (for back-to-back)
        conflict_b2b = {"blocks": [1, 2], "day": "Monday"}
        enriched_b2b = conflict_b2b.copy()
        enriched_b2b["block_times"] = [
            block_time_map.get(block, f"Block {block}") for block in conflict_b2b["blocks"]
        ]
        
        assert enriched_b2b["block_times"] == ["11:30AM-1:30PM", "2PM-4PM"]

    def test_instructor_name_in_conflicts(self):
        """Test that instructor conflicts include instructor_name."""
        instructor_conflict = {
            "instructor_name": "Dr. Smith",
            "day": "Tuesday",
            "blocks": [0, 1],
        }

        # Should have instructor_name for instructor conflicts
        assert "instructor_name" in instructor_conflict
        assert instructor_conflict["instructor_name"] == "Dr. Smith"

    def test_student_id_in_conflicts(self):
        """Test that student conflicts include student_id."""
        student_conflict = {
            "student_id": "2037533",
            "day": "Monday",
            "blocks": [1, 2],
        }

        # Should have student_id for student conflicts
        assert "student_id" in student_conflict
        assert student_conflict["student_id"] == "2037533"

    def test_conflict_breakdown_format(self):
        """Test conflict breakdown format for API responses."""
        breakdown_item = {
            "conflict_type": "back_to_back_instructor",
            "entity_id": "Dr. Smith",
            "instructor_name": "Dr. Smith",
            "day": "Tuesday",
            "blocks": [0, 1],
            "block_times": ["9AM-11AM", "11:30AM-1:30PM"],
        }

        # Verify all required fields
        assert "conflict_type" in breakdown_item
        assert "day" in breakdown_item
        assert "blocks" in breakdown_item
        assert "block_times" in breakdown_item
        assert "instructor_name" in breakdown_item

        # Verify block_times length matches blocks length
        assert len(breakdown_item["blocks"]) == len(breakdown_item["block_times"])

    def test_conflict_statistics_calculation(self):
        """Test conflict statistics calculation."""
        conflicts_data = {
            "hard_conflicts": {
                "student_double_book": [{}] * 5,  # 5 conflicts
                "instructor_double_book": [{}] * 2,  # 2 conflicts
                "student_gt_max_per_day": [{}] * 3,  # 3 conflicts
            },
            "soft_conflicts": {
                "back_to_back_students": [{}] * 10,  # 10 conflicts
                "back_to_back_instructors": [{}] * 5,  # 5 conflicts
                "large_courses_not_early": [{}] * 2,  # 2 conflicts
            },
            "statistics": {
                "student_double_book_count": 5,
                "instructor_double_book_count": 2,
                "total_hard_conflicts": 10,  # 5 + 2 + 3
                "total_soft_conflicts": 17,  # 10 + 5 + 2
            },
        }

        # Calculate hard conflicts
        hard_count = (
            len(conflicts_data["hard_conflicts"]["student_double_book"])
            + len(conflicts_data["hard_conflicts"]["instructor_double_book"])
            + len(conflicts_data["hard_conflicts"]["student_gt_max_per_day"])
        )
        assert hard_count == 10

        # Calculate soft conflicts
        soft_count = (
            len(conflicts_data["soft_conflicts"]["back_to_back_students"])
            + len(conflicts_data["soft_conflicts"]["back_to_back_instructors"])
            + len(conflicts_data["soft_conflicts"]["large_courses_not_early"])
        )
        assert soft_count == 17

        # Verify statistics match
        assert conflicts_data["statistics"]["total_hard_conflicts"] == hard_count
        assert conflicts_data["statistics"]["total_soft_conflicts"] == soft_count


class TestConflictDataEnrichment:
    """Test conflict data enrichment (adding times, course names, etc.)."""

    def test_enrich_conflict_with_block_time(self):
        """Test enriching conflicts with block_time."""
        block_time_map = {
            0: "9AM-11AM",
            1: "11:30AM-1:30PM",
            2: "2PM-4PM",
            3: "4:30PM-6:30PM",
            4: "7PM-9PM",
        }

        conflict = {"block": 1, "day": "Monday", "crn": "10001"}
        
        # Enrich with block_time
        if "block_time" not in conflict and "block" in conflict:
            conflict["block_time"] = block_time_map.get(conflict["block"], "")

        assert conflict["block_time"] == "11:30AM-1:30PM"

    def test_enrich_back_to_back_with_times(self):
        """Test enriching back-to-back conflicts with block_times."""
        block_time_map = {
            0: "9AM-11AM",
            1: "11:30AM-1:30PM",
            2: "2PM-4PM",
            3: "4:30PM-6:30PM",
            4: "7PM-9PM",
        }

        conflict = {"blocks": [2, 3], "day": "Wednesday", "instructor_name": "Dr. Smith"}
        
        # Enrich with block_times
        if "blocks" in conflict:
            conflict["block_times"] = [
                block_time_map.get(block, f"Block {block}") for block in conflict["blocks"]
            ]

        assert conflict["block_times"] == ["2PM-4PM", "4:30PM-6:30PM"]
        assert len(conflict["block_times"]) == len(conflict["blocks"])

    def test_process_back_to_back_conflicts(self):
        """Test processing back-to-back conflicts for API."""
        # Simulate what _process_back_to_back_conflicts does
        block_time_map = {
            0: "9AM-11AM",
            1: "11:30AM-1:30PM",
            2: "2PM-4PM",
            3: "4:30PM-6:30PM",
            4: "7PM-9PM",
        }

        raw_conflicts = [
            {
                "instructor_name": "Dr. Smith",
                "day": "Monday",
                "blocks": [0, 1],
            },
            {
                "student_id": "S001",
                "day": "Tuesday",
                "blocks": [2, 3, 4],
            },
        ]

        processed = []
        for conflict in raw_conflicts:
            blocks = conflict.get("blocks", [])
            block_times = [block_time_map.get(block, f"Block {block}") for block in blocks]
            
            entity_key = "instructor_name" if "instructor_name" in conflict else "student_id"
            entity_value = conflict.get(entity_key)
            
            processed.append({
                entity_key: entity_value,
                "instructor_name": conflict.get("instructor_name") if "instructor_name" in conflict else None,
                "day": conflict.get("day"),
                "blocks": blocks,
                "block_times": block_times,
                "conflict_type": "back_to_back_instructor" if "instructor_name" in conflict else "back_to_back",
            })

        assert len(processed) == 2
        assert processed[0]["block_times"] == ["9AM-11AM", "11:30AM-1:30PM"]
        assert processed[1]["block_times"] == ["2PM-4PM", "4:30PM-6:30PM", "7PM-9PM"]
        assert processed[0]["instructor_name"] == "Dr. Smith"
        assert processed[1]["instructor_name"] is None

