"""
DSATUR Exam Scheduling Algorithm - Main Module

This module provides the DSATURExamGraph class, which implements a complete
exam scheduling system using the DSATUR (Degree of Saturation) graph coloring algorithm.

The algorithm works in phases:
1. Graph Construction: Build conflict graph from enrollment data
2. Graph Coloring: Assign time slot groups using DSATUR
3. Scheduling: Assign specific time slots to courses
4. Room Assignment: Assign rooms based on capacity
5. Reporting: Generate conflict and violation reports

All exams are ALWAYS placed, even if conflicts occur. Conflicts are tracked
and reported but do not prevent scheduling.

CONFLICTS (tracked but don't block placement):
  - Student double-booked in the same (day, block) - CONFLICT
  - Instructor double-booked in the same (day, block) - CONFLICT
  - Student has more than max_per_day exams in one day - CONFLICT
  - Instructor has more than max_instructor_per_day exams in one day - CONFLICT

SOFT preferences (warnings, minimized in this order; controlled by weights):
  1) Large courses (>=100) earlier in week
  2) Avoid back-to-back for students (WARNING only)
  3) Avoid back-to-back for instructors (WARNING only, optional, lower weight)

Inputs can be in *either* schema:
  Census:      [CRN, course_ref, num_students]  OR  [CRN, CourseID, num_students]
  Enrollment:  [student_id, CRN, instructor_name]  OR  [Student_PIDM, CRN, Instructor Name]
  Classrooms:  [room_name, capacity]
"""

from collections import defaultdict

import networkx as nx
import pandas as pd

from src.algorithms.dsatur_graph import DSATURGraphBuilder
from src.algorithms.dsatur_scheduling import DSATURSchedulingMixin


class DSATURExamGraph(DSATURSchedulingMixin):
    """
    DSATUR-based exam scheduler
    
    This class orchestrates the complete exam scheduling workflow:
    1. Normalizes input data
    2. Builds conflict graph
    3. Colors graph using DSATUR algorithm
    4. Schedules exams to time slots
    5. Assigns rooms
    6. Generates reports
    
    The class inherits scheduling methods from DSATURSchedulingMixin and
    uses DSATURGraphBuilder for graph operations.
    """

    def __init__(
        self,
        census: pd.DataFrame,
        enrollment: pd.DataFrame,
        classrooms: pd.DataFrame,
        weight_large_late: int = 1,
        weight_b2b_student: int = 6,
        weight_b2b_instructor: int = 2,
        student_max_per_day: int = 2,
        instructor_max_per_day: int = 2,
    ):
        """
        Initialize the DSATUR exam scheduler.
        
        Args:
            census: DataFrame with course information (CRN, course_ref/CourseID, num_students)
            enrollment: DataFrame with enrollment data (student_id/Student_PIDM, CRN, instructor_name/Instructor Name)
            classrooms: DataFrame with room information (room_name, capacity)
            weight_large_late: Weight for penalizing large courses scheduled late (default: 1)
            weight_b2b_student: Weight for penalizing student back-to-back exams (default: 6)
            weight_b2b_instructor: Weight for penalizing instructor back-to-back exams (default: 2)
            student_max_per_day: Maximum exams per student per day (default: 2)
            instructor_max_per_day: Maximum exams per instructor per day (default: 2)
        """
        # Normalize input data to canonical format
        self.census, self.enrollment, self.classrooms = DSATURGraphBuilder._normalize_inputs(
            census, enrollment, classrooms
        )

        # Filter enrollment to only include CRNs that exist in census
        # This prevents errors from orphaned enrollment records
        crn_census = set(self.census["CRN"].unique())
        self.enrollment = self.enrollment[
            self.enrollment["CRN"].isin(crn_census)
        ].copy()

        # Store soft constraint weights
        # These control the relative importance of different preferences
        self.weight_large_late = int(weight_large_late)
        self.weight_b2b_student = int(weight_b2b_student)
        self.weight_b2b_instructor = int(weight_b2b_instructor)
        self.student_max_per_day = int(student_max_per_day)
        self.instructor_max_per_day = int(instructor_max_per_day)

        # Core data structures
        self.G = nx.Graph()  # Conflict graph (nodes = courses, edges = conflicts)
        self.colors = {}  # CRN -> DSATUR color (time slot group)
        self.assignment = {}  # CRN -> (day, block) final time slot assignment
        self.unassigned = set()  # CRNs that could not be placed (should be empty)
        
        # Slot tracking for efficient conflict checking
        self.block_exam_count = defaultdict(int)  # (day, block) -> number of exams
        self.block_seat_load = defaultdict(int)  # (day, block) -> total students
        self.slot_to_crns = defaultdict(list)  # (day, block) -> [crn1, crn2, ...]

        # Time grid configuration
        # 7 days (Monday-Sunday), 5 blocks per day
        self.exam_blocks = [(d, b) for d in range(7) for b in range(5)]
        self.day_names = [
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
            "Sunday",
        ]
        self.block_times = {
            0: "9:00-11:00",
            1: "11:30-1:30",
            2: "2:00-4:00",
            3: "4:30-6:30",
            4: "7:00-9:00",
        }

        # Allowed slots (set later by dsatur_schedule; default = all 7 days)
        self.max_days = 7
        self.usable_blocks = [(d, b) for d in range(self.max_days) for b in range(5)]

        # Caches for efficient lookups (built during graph construction)
        self.students_by_crn = {}  # CRN -> set(student_id)
        self.instructors_by_crn = {}  # CRN -> set(instructor_name)

        # Track instructor assignments persistently
        self.instructor_sched = defaultdict(list)  # instructor_name -> [(day, block)]

        # Diagnostics and reporting
        self.fallback_courses = set()  # Courses that were logically impossible to place
        self.unplaced_reason_counts = {}  # CRN -> {reason: count}

        # Conflict tracking (for reporting, not blocking)
        # List of conflict records: (type, entity_id, day, block, crn, conflicting_crn_or_list)
        self.conflicts = []

        # Post-schedule reports (DataFrames)
        self.student_soft_violations = pd.DataFrame()
        self.instructor_soft_violations = pd.DataFrame()
        self.large_courses_not_early = pd.DataFrame()

        # Graph builder instance for graph operations
        self._graph_builder = DSATURGraphBuilder()

    # ---------- graph construction and coloring ----------
    def build_graph(self):
        """
        Build the conflict graph from course and enrollment data.
        
        Creates a NetworkX graph where:
        - Nodes = courses (CRNs) with metadata (course_ref, size)
        - Edges = conflicts (courses that share students or instructors)
        
        Also builds lookup caches:
        - students_by_crn: Maps each CRN to its set of enrolled students
        - instructors_by_crn: Maps each CRN to its set of instructors
        
        This must be called before dsatur_color().
        
        Returns:
            None (modifies self.G, self.students_by_crn, self.instructors_by_crn)
        """
        # Build graph and caches using the graph builder
        self.G, self.students_by_crn, self.instructors_by_crn = (
            self._graph_builder.build_graph(self.census, self.enrollment)
        )

    def dsatur_color(self):
        """
        Apply DSATUR graph coloring algorithm to assign time slot groups.
        
        DSATUR (Degree of Saturation) is a greedy graph coloring algorithm that:
        1. Selects the node with highest saturation degree (most colored neighbors)
        2. Assigns the smallest available color
        3. Repeats until all nodes are colored
        
        The color assigned to each course represents a time slot group.
        Courses with the same color can potentially be scheduled at the same time
        (if they don't have other conflicts beyond the graph edges).
        
        This must be called after build_graph() and before dsatur_schedule().
        
        Returns:
            Dictionary mapping CRN -> color (integer)
            
        Raises:
            RuntimeError: If graph is empty (build_graph() not called)
        """
        if self.G.number_of_nodes() == 0:
            raise RuntimeError("Call build_graph() first.")
        
        # Use graph builder to perform coloring
        self.colors = self._graph_builder.dsatur_color(self.G)
        return self.colors


# ---------- export utility function ----------
def export_student_schedule(
    g_backend,
    enrollment_df: pd.DataFrame,
    df_schedule: pd.DataFrame,
    base_name: str = "student_schedule",
    include_instructor: bool = True,
    add_blank_between_students: bool = False,
):
    """
    Export schedule to student-focused CSV format.
    
    Creates a CSV file with one row per student-exam combination, sorted
    chronologically by student and then by exam time.
    
    This is useful for generating individual student schedules or
    distributing exam information to students.
    
    Args:
        g_backend: DSATURExamGraph instance with assignment dictionary
        enrollment_df: DataFrame with student enrollment data
        df_schedule: DataFrame with scheduled exams (from assign_rooms())
        base_name: Base name for output file (default: "student_schedule")
        include_instructor: Whether to include instructor names (default: True)
        add_blank_between_students: Whether to add blank rows between students (default: False)
        
    Returns:
        DataFrame with student schedule data
        
    Raises:
        ValueError: If required columns are missing
        
    Output:
        Creates CSV file: {base_name}_by_student_long.csv
    """
    import re

    # Helper function to clean CRN values (handles Excel float conversion)
    def clean_crn(v):
        """
        Convert CRN to clean string format.
        
        Handles cases where CRNs are stored as floats (e.g., 11310.0 -> "11310")
        """
        try:
            if pd.isna(v):
                return None
            return str(int(float(v))).strip()
        except Exception:
            return str(v).strip()

    # Normalize enrollment columns (handle legacy schema names)
    enroll = enrollment_df.copy()
    col_renames = {}
    if "Student_PIDM" in enroll.columns and "student_id" not in enroll.columns:
        col_renames["Student_PIDM"] = "student_id"
    if "Instructor Name" in enroll.columns and "instructor_name" not in enroll.columns:
        col_renames["Instructor Name"] = "instructor_name"
    if col_renames:
        enroll = enroll.rename(columns=col_renames)

    # Validate required columns exist
    need_cols = {"student_id", "CRN"}
    missing = need_cols - set(enroll.columns)
    if missing:
        raise ValueError(
            f"enrollment_df is missing required columns after normalization: {sorted(missing)}"
        )

    # Keep only necessary columns
    keep_cols = ["student_id", "CRN"] + (
        ["instructor_name"] if "instructor_name" in enroll.columns else []
    )
    enroll = enroll.loc[:, keep_cols].copy()

    # Clean and normalize data types
    enroll["student_id"] = enroll["student_id"].astype(str).str.strip()
    enroll["CRN"] = enroll["CRN"].apply(clean_crn)
    if "instructor_name" in enroll.columns:
        enroll["instructor_name"] = (
            enroll["instructor_name"].fillna("").astype(str).str.strip()
        )

    # Remove empty records and duplicates
    enroll = enroll.dropna(subset=["student_id", "CRN"])
    enroll = enroll[enroll["CRN"] != ""]
    enroll = enroll.drop_duplicates(subset=["student_id", "CRN"])

    # Build instructor mapping (CRN -> semicolon-joined instructor names)
    instr_map = {}
    if include_instructor and "instructor_name" in enroll.columns:
        tmp = enroll.loc[
            enroll["instructor_name"] != "", ["CRN", "instructor_name"]
        ].copy()
        if not tmp.empty:
            instr_map = (
                tmp.groupby("CRN")["instructor_name"]
                .apply(
                    lambda s: "; ".join(
                        sorted({x.strip() for x in s if x and str(x).strip()})
                    )
                )
                .to_dict()
            )

    # Prepare schedule metadata
    sched = df_schedule.copy()
    if "CRN" not in sched.columns:
        raise ValueError("df_schedule must contain a 'CRN' column.")
    sched["CRN"] = sched["CRN"].apply(clean_crn)
    meta = sched.set_index("CRN").to_dict(orient="index")

    # Get unassigned CRNs (if any)
    unassigned = set(getattr(g_backend, "unassigned", set()) or [])

    # Build student schedule rows
    long_rows = []

    # Process each student
    for sid, grp in enroll.groupby("student_id", sort=True):
        items = []
        for raw_crn in grp["CRN"]:
            crn = clean_crn(raw_crn)
            if crn in unassigned:
                continue  # Skip unassigned courses
            if crn in getattr(g_backend, "assignment", {}) and crn in meta:
                day_idx, block_idx = g_backend.assignment[crn]
                info = meta[crn]
                items.append((day_idx, block_idx, crn, info))

        # Sort exams chronologically for this student
        items.sort(key=lambda x: (x[0], x[1]))

        # Create rows for each exam
        for i, (d, b, crn, info) in enumerate(items, 1):
            # Extract block number from block string (e.g., "2 (2:00-4:00)" -> 2)
            block_str = str(info.get("Block", ""))
            m = re.search(r"(\d+)", block_str)
            block_num = int(m.group(1)) if m else b

            row = {
                "student_id": sid,
                "exam_num": i,
                "CRN": crn,
                "Course": info.get("Course", ""),
                "Day": info.get("Day", ""),
                "Block": info.get("Block", ""),
                "Room": info.get("Room", ""),
                "Capacity": info.get("Capacity", ""),
                "Size": info.get("Size", ""),
                "Valid": info.get("Valid", ""),
                "Day_idx": d,
                "Block_num": block_num,
            }
            if include_instructor:
                row["Instructor"] = instr_map.get(crn, "")
            long_rows.append(row)

        # Optionally add blank separator row between students
        if add_blank_between_students and items:
            keys = list(long_rows[-1].keys())
            long_rows.append(dict.fromkeys(keys, ""))

    # Create final DataFrame
    long_df = pd.DataFrame(long_rows)

    # Sort if not using blank separators
    if not add_blank_between_students and not long_df.empty:
        sort_cols = [
            c
            for c in ["student_id", "Day_idx", "Block_num", "exam_num"]
            if c in long_df.columns
        ]
        long_df = long_df.sort_values(sort_cols, kind="mergesort")

    # Save to CSV
    out_path = f"{base_name}_by_student_long.csv"
    long_df.to_csv(out_path, index=False)

    placed = int(long_df["CRN"].ne("").sum()) if not long_df.empty else 0
    print(f"SUCCESS: Saved {placed} exam records to {out_path}")
    if unassigned:
        print(
            f"WARNING: Skipped {len(unassigned)} unassigned CRNs (hard-rule placement impossible)."
        )

    return long_df
