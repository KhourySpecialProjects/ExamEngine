"""
DSATUR Graph Building and Coloring Module

This module handles the graph construction and coloring phases of the DSATUR algorithm.
It includes:
- Input data normalization
- Conflict graph construction (nodes = courses, edges = conflicts)
- DSATUR graph coloring to assign time slots

The graph represents courses as nodes, with edges connecting courses that have
conflicting students or instructors (i.e., cannot be scheduled at the same time).
"""

from collections import defaultdict
from itertools import combinations

import networkx as nx
import pandas as pd


class DSATURGraphBuilder:
    """
    Handles graph construction and coloring for the DSATUR algorithm.
    
    This class builds a conflict graph where:
    - Nodes represent courses (CRNs)
    - Edges connect courses that share students or instructors (conflicts)
    - Graph coloring assigns time slots to courses
    """

    @staticmethod
    def _normalize_inputs(census, enrollment, classrooms):
        """
        Normalize input DataFrames to a canonical format.
        
        Handles multiple input schemas and converts them to a standard format:
        - Census: [CRN, course_ref, num_students]
        - Enrollment: [student_id, CRN, instructor_name]
        - Classrooms: [room_name, capacity]
        
        Args:
            census: DataFrame with course information
            enrollment: DataFrame with student enrollment data
            classrooms: DataFrame with room information
            
        Returns:
            Tuple of (normalized_census, normalized_enrollment, normalized_classrooms)
            
        Raises:
            ValueError: If required columns are missing
        """
        c = census.copy()
        e = enrollment.copy()
        r = classrooms.copy()

        # Rename to canonical columns (handle legacy schema names)
        c = c.rename(columns={"CourseID": "course_ref"})
        e = e.rename(
            columns={"Student_PIDM": "student_id", "Instructor Name": "instructor_name"}
        )

        # Keep only required columns (ignore extras)
        need_c = ["CRN", "course_ref", "num_students"]
        need_e = ["student_id", "CRN", "instructor_name"]
        need_r = ["room_name", "capacity"]

        # Validate required columns exist
        missing_c = set(need_c) - set(c.columns)
        missing_e = set(need_e) - set(e.columns)
        missing_r = set(need_r) - set(r.columns)
        if missing_c:
            raise ValueError(f"Census missing columns: {sorted(missing_c)}")
        if missing_e:
            raise ValueError(f"Enrollment missing columns: {sorted(missing_e)}")
        if missing_r:
            raise ValueError(f"Classrooms missing columns: {sorted(missing_r)}")

        c = c[need_c].copy()
        e = e[need_e].copy()
        r = r[need_r].copy()

        # Clean CRNs to string without ".0" (handles Excel float conversion)
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

        c["CRN"] = c["CRN"].apply(clean_crn)
        e["CRN"] = e["CRN"].apply(clean_crn)

        # Ensure proper data types
        c["num_students"] = (
            pd.to_numeric(c["num_students"], errors="coerce").fillna(0).astype(int)
        )
        e["student_id"] = e["student_id"].astype(str)
        e["instructor_name"] = e["instructor_name"].fillna("").astype(str).str.strip()
        r["capacity"] = (
            pd.to_numeric(r["capacity"], errors="coerce").fillna(0).astype(int)
        )

        # Filter empties & dedupe enrollment to prevent false collisions
        # This ensures each student-CRN pair appears only once
        c = c.dropna(subset=["CRN"])
        e = e.dropna(subset=["CRN", "student_id"])
        e = e.drop_duplicates(subset=["student_id", "CRN"]).copy()

        return c, e, r

    def build_graph(self, census, enrollment):
        """
        Build the conflict graph from course and enrollment data.
        
        Creates a NetworkX graph where:
        - Nodes = courses (CRNs)
        - Edges = conflicts (courses that share students or instructors)
        
        Process:
        1. Add all courses as nodes with metadata (course_ref, size)
        2. Build student-to-CRN and instructor-to-CRN mappings
        3. Add edges for courses sharing students
        4. Add edges for courses sharing instructors
        
        Args:
            census: Normalized census DataFrame
            enrollment: Normalized enrollment DataFrame
            
        Returns:
            Tuple of (graph, students_by_crn_dict, instructors_by_crn_dict)
        """
        G = nx.Graph()
        
        # Step 1: Add all courses as nodes
        # Each node stores course metadata: course_ref and enrollment size
        for _, row in census.iterrows():
            G.add_node(
                row["CRN"],
                course_ref=row.get("course_ref", ""),
                size=int(row.get("num_students", 0) or 0),
            )

        # Step 2: Build mappings of students/instructors per CRN
        # These are used for conflict detection and scheduling
        students_by_crn = (
            enrollment.groupby("CRN")["student_id"].apply(set).to_dict()
            if not enrollment.empty
            else {}
        )

        # Collect all instructor names for each CRN (courses can have multiple instructors)
        tmp = (
            enrollment[enrollment["instructor_name"] != ""]
            .groupby("CRN")["instructor_name"]
            .apply(lambda s: {x for x in s if x})
        )
        instructors_by_crn = tmp.to_dict()

        crn_set = set(census["CRN"])

        # Step 3: Add edges for courses sharing students
        # If two courses share a student, they cannot be scheduled at the same time
        for _, grp in enrollment.groupby("student_id"):
            crns = [c for c in grp["CRN"].tolist() if c in crn_set]
            # Create edges between all pairs of courses this student is enrolled in
            for a, b in combinations(crns, 2):
                G.add_edge(a, b, conflict="student")

        # Step 4: Add edges for courses sharing instructors
        # If two courses share an instructor, they cannot be scheduled at the same time
        instr_to_crns = defaultdict(list)
        for crn, instrs in instructors_by_crn.items():
            for instr in instrs:
                instr_to_crns[instr].append(crn)
        
        # Add edges for courses taught by the same instructor
        for crns in instr_to_crns.values():
            if len(crns) > 1:
                for a, b in combinations([c for c in crns if c in crn_set], 2):
                    # If edge already exists (student conflict), update label
                    if G.has_edge(a, b):
                        G[a][b]["conflict"] = "student|instructor"
                    else:
                        G.add_edge(a, b, conflict="instructor")

        return G, students_by_crn, instructors_by_crn

    def dsatur_color(self, graph):
        """
        Apply DSATUR (Degree of Saturation) graph coloring algorithm.
        
        DSATUR is a greedy graph coloring algorithm that:
        1. Selects the node with the highest saturation degree (most colored neighbors)
        2. Assigns the smallest available color
        3. Repeats until all nodes are colored
        
        The color assigned to each course represents a time slot group.
        Courses with the same color can potentially be scheduled at the same time
        (if they don't have other conflicts).
        
        Args:
            graph: NetworkX graph with courses as nodes
            
        Returns:
            Dictionary mapping CRN -> color (integer)
            
        Raises:
            RuntimeError: If graph is empty
        """
        if graph.number_of_nodes() == 0:
            raise RuntimeError("Cannot color empty graph. Build graph first.")
        
        # Use NetworkX's built-in DSATUR coloring strategy
        colors = nx.coloring.greedy_color(graph, strategy="DSATUR")
        return colors

