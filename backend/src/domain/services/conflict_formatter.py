from typing import Any

from src.domain.constants import BLOCK_TIMES


class ConflictFormatter:
    """
    Formats conflict analysis data for API responses.

    Enriches raw conflict data with:
    - Block time labels (e.g., "9AM-11AM")
    - Course names (resolved from CRN)
    - Human-readable conflict type labels

    """

    def __init__(self, course_name_map: dict[str, str]):
        """
        Initialize formatter with course name mapping.

        Args:
            course_name_map: Dict mapping CRN (as string) to course code
        """
        self.course_name_map = course_name_map

    def format_conflicts(self, conflict_analysis) -> dict[str, Any]:
        """
        Format conflict analysis for API response.

        Args:
            conflict_analysis: ConflictAnalyses ORM object (or None)

        Returns:
            Formatted dict with total, breakdown (flat array), and details
        """
        if conflict_analysis is None:
            return self._empty_response()

        if not conflict_analysis.conflicts:
            return self._empty_response()

        conflicts_json = conflict_analysis.conflicts
        hard = conflicts_json.get("hard_conflicts", {})
        soft = conflicts_json.get("soft_conflicts", {})

        # Build flat breakdown array
        breakdown = []
        breakdown.extend(
            self._process_double_book_conflicts(
                hard.get("student_double_book", []), "student_double_book"
            )
        )
        breakdown.extend(
            self._process_double_book_conflicts(
                hard.get("instructor_double_book", []), "instructor_double_book"
            )
        )
        breakdown.extend(
            self._process_max_per_day_conflicts(
                hard.get("student_gt_max_per_day", []), "student_gt_max_per_day"
            )
        )
        breakdown.extend(
            self._process_max_per_day_conflicts(
                hard.get("instructor_gt_max_per_day", []), "instructor_gt_max_per_day"
            )
        )
        breakdown.extend(
            self._process_back_to_back_conflicts(
                soft.get("back_to_back_students", []), "back_to_back"
            )
        )
        breakdown.extend(
            self._process_back_to_back_conflicts(
                soft.get("back_to_back_instructors", []), "back_to_back_instructor"
            )
        )
        breakdown.extend(
            self._process_large_course_conflicts(
                soft.get("large_courses_not_early", [])
            )
        )

        # Get total from statistics if available
        statistics = conflicts_json.get("statistics", {})
        total = statistics.get("total_hard_conflicts", 0)

        return {
            "total": total,
            "breakdown": breakdown,
            "details": {},  # Frontend doesn't use this much
        }

    def _process_double_book_conflicts(
        self, conflicts: list[dict], conflict_type: str
    ) -> list[dict]:
        """Process double-booking conflicts into flat records."""
        result = []
        for conflict in conflicts:
            record = {
                "conflict_type": conflict_type,
                "entity_id": conflict.get("entity_id"),
                "day": conflict.get("day"),
                "block": conflict.get("block"),
                "block_time": conflict.get("block_time")
                or BLOCK_TIMES.get(conflict.get("block"), ""),
                "crn": conflict.get("crn"),
                "course": self._get_course_name(
                    conflict.get("crn"), conflict.get("course")
                ),
                "conflicting_crn": conflict.get("conflicting_crn"),
                "conflicting_course": self._get_course_name(
                    conflict.get("conflicting_crn"), conflict.get("conflicting_course")
                ),
            }
            result.append(record)
        return result

    def _process_max_per_day_conflicts(
        self, conflicts: list[dict], conflict_type: str
    ) -> list[dict]:
        """Process max-per-day violations into flat records."""
        result = []
        for conflict in conflicts:
            record = {
                "conflict_type": conflict_type,
                "entity_id": conflict.get("entity_id") or conflict.get("student_id"),
                "student_id": conflict.get("student_id") or conflict.get("entity_id"),
                "day": conflict.get("day"),
                "block": conflict.get("block"),
                "block_time": conflict.get("block_time")
                or BLOCK_TIMES.get(conflict.get("block"), ""),
                "crn": conflict.get("crn"),
                "course": self._get_course_name(
                    conflict.get("crn"), conflict.get("course")
                ),
                "conflicting_crns": conflict.get("conflicting_crns", []),
                "conflicting_courses": [
                    self._get_course_name(crn)
                    for crn in conflict.get("conflicting_crns", [])
                ],
            }
            result.append(record)
        return result

    def _process_back_to_back_conflicts(
        self, conflicts: list[dict], conflict_type: str
    ) -> list[dict]:
        """Process back-to-back conflicts into flat records."""
        result = []
        for conflict in conflicts:
            record = {
                "conflict_type": conflict_type,
                "entity_id": conflict.get("instructor_name")
                or conflict.get("student_id"),
                "student_id": conflict.get("student_id"),
                "day": conflict.get("day"),
                "blocks": conflict.get("blocks", []),
                "block_times": conflict.get("block_times", []),
            }
            result.append(record)
        return result

    def _process_large_course_conflicts(self, conflicts: list[dict]) -> list[dict]:
        """Process large-course-not-early conflicts."""
        result = []
        for conflict in conflicts:
            record = {
                "conflict_type": "large_course_not_early",
                "crn": conflict.get("crn"),
                "course": self._get_course_name(
                    conflict.get("crn"), conflict.get("course")
                ),
                "size": conflict.get("size"),
                "day": conflict.get("day"),
                "block": conflict.get("block"),
                "block_time": conflict.get("block_time")
                or BLOCK_TIMES[conflict.get("block")],
            }
            result.append(record)
        return result

    def _get_course_name(self, crn: str | None, fallback: str | None = None) -> str:
        """Get course name from CRN, with fallback."""
        if crn:
            name = self.course_name_map.get(str(crn))
            if name:
                return name
        return fallback or "Unknown"

    def get_conflicting_crns(self, conflict_analysis) -> set[str]:
        """
        Extract all CRNs involved in hard conflicts.

        Used by schedule data builders to mark exams as invalid.

        Args:
            conflict_analysis: ConflictAnalyses ORM object (or None)

        Returns:
            Set of CRN strings that have conflicts
        """
        crns = set()

        if not conflict_analysis or not conflict_analysis.conflicts:
            return crns

        hard_conflicts = conflict_analysis.conflicts.get("hard_conflicts", {})

        for conflicts_list in hard_conflicts.values():
            for conflict in conflicts_list:
                # Primary CRN
                crn = conflict.get("crn")
                if crn:
                    crns.add(str(crn))

                # Single conflicting CRN
                conflicting_crn = conflict.get("conflicting_crn")
                if conflicting_crn:
                    crns.add(str(conflicting_crn))

                # Multiple conflicting CRNs (for gt_max_per_day)
                for c_crn in conflict.get("conflicting_crns", []):
                    if c_crn:
                        crns.add(str(c_crn))

        return crns

    @staticmethod
    def _empty_response() -> dict[str, Any]:
        """Return empty conflicts response structure."""
        return {
            "total": 0,
            "breakdown": [],
            "details": {},
        }
