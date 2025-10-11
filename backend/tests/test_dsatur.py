import pandas as pd
import networkx as nx
import copy
from backend.src.algorithms.dsatur_scheduler import DSATURExamGraph

# Helper to run the scheduler with given parameters and return graph and schedule DataFrame

def run_scheduler(census, enrollment, rooms,
                  max_per_day=3, avoid_back_to_back=True, max_days=7):
    g = DSATURExamGraph(census, enrollment, rooms)
    g.build_graph()
    g.dsatur_color()
    g.dsatur_schedule(max_per_day=max_per_day,
                      avoid_back_to_back=avoid_back_to_back,
                      max_days=max_days)
    df = g.assign_rooms()
    return g, df

# Tests below

def test_basic_two_courses_no_conflict():
    census = pd.DataFrame({
        "CRN": [1, 2],
        "course_ref": ["CS101", "CS102"],
        "num_students": [30, 25]
    })
    enrollment = pd.DataFrame({
        "student_id": [1, 1, 2, 3],
        "CRN": [1, 2, 1, 2]
    })
    rooms = pd.DataFrame({
        "room_name": ["A", "B"],
        "capacity": [40, 30]
    })

    g, df = run_scheduler(census, enrollment, rooms)
    assert len(df) == 2
    assert df["Valid"].all()
    assert g.count_schedule_conflicts()[0] == 0


def test_shared_student_forces_different_blocks():
    # One student in both courses -> they must not land in same (day, block)
    census = pd.DataFrame({
        "CRN": [10, 20],
        "course_ref": ["MATH", "PHYS"],
        "num_students": [50, 60]
    })
    enrollment = pd.DataFrame({
        "student_id": [111, 111],
        "CRN": [10, 20]
    })
    rooms = pd.DataFrame({
        "room_name": ["X", "Y"],
        "capacity": [100, 100]
    })

    g, df = run_scheduler(census, enrollment, rooms, max_days=1)
    # Ensure assigned blocks differ for same day
    a = g.assignment[10]
    b = g.assignment[20]
    assert a[0] == b[0]  # same day (since max_days=1)
    assert a[1] != b[1]  # different blocks
    assert g.count_schedule_conflicts()[0] == 0


def test_avoid_back_to_back_true_prevents_adjacent_blocks():
    # One student with 2 courses; avoid back-to-back should separate blocks
    census = pd.DataFrame({
        "CRN": [1, 2],
        "course_ref": ["A", "B"],
        "num_students": [10, 10]
    })
    enrollment = pd.DataFrame({
        "student_id": [5, 5],
        "CRN": [1, 2]
    })
    classrooms = pd.DataFrame({"room_name": ["R"], "capacity": [100]})

    g, _ = run_scheduler(census, enrollment, classrooms, avoid_back_to_back=True, max_days=1)
    (d1, b1) = g.assignment[1]
    (d2, b2) = g.assignment[2]
    # Same day, not adjacent blocks
    assert d1 == d2
    assert abs(b1 - b2) != 1
    assert g.count_schedule_conflicts()[0] == 0


def test_back_to_back_allowed_if_flag_off():
    # Same as above but allow back-to-back -> adjacent blocks are fine
    census = pd.DataFrame({
        "CRN": [1, 2],
        "course_ref": ["A", "B"],
        "num_students": [10, 10]
    })
    enrollment = pd.DataFrame({
        "student_id": [5, 5],
        "CRN": [1, 2]
    })
    rooms = pd.DataFrame({"room_name": ["R"], "capacity": [100]})

    g, _ = run_scheduler(census, enrollment, rooms, avoid_back_to_back=False, max_days=1)
    (d1, b1) = g.assignment[1]
    (d2, b2) = g.assignment[2]
    assert d1 == d2  # same day
    # Adjacent blocks are allowed, so either same or +/-1; verify not flagged
    total_conflicts, _, _ = g.count_schedule_conflicts(check_back_to_back=False)
    assert total_conflicts == 0


def test_cap_three_exams_per_day_violation_triggers_fallback_conflict():
    # 4 courses for one student, only 1 day available => fallback must violate the 3/day constraint
    census = pd.DataFrame({
        "CRN": [1, 2, 3, 4],
        "course_ref": ["C1", "C2", "C3", "C4"],
        "num_students": [10, 10, 10, 10]
    })
    enrollment = pd.DataFrame({
        "student_id": [7, 7, 7, 7],
        "CRN": [1, 2, 3, 4]
    })
    rooms = pd.DataFrame({
        "room_name": ["R1", "R2", "R3", "R4", "R5"],
        "capacity": [100, 100, 100, 100, 100]
    })

    g, _ = run_scheduler(census, enrollment, rooms, max_per_day=3, max_days=1)
    total_conflicts, _, breakdown = g.count_schedule_conflicts()
    # Expect at least one conflict (>3 exams in a day)
    assert total_conflicts >= 1
    assert any(breakdown["conflict_type"].str.contains(">3_per_day"))


def test_room_best_fit_smallest_that_fits():
    # Sizes 10, 49, 50; rooms 10,50 -> ensure 49 goes to 50, 10 to 10, and 50 to 50 (fallback/choice)
    census = pd.DataFrame({
        "CRN": [101, 102, 103],
        "course_ref": ["C1", "C2", "C3"],
        "num_students": [10, 49, 50]
    })
    # No shared students needed; schedule anywhere
    enrollment = pd.DataFrame(columns=["student_id", "CRN"])
    rooms = pd.DataFrame({
        "room_name": ["S", "L"],
        "capacity": [10, 50]
    })

    g, df = run_scheduler(census, enrollment, rooms)
    # Validate mapping by capacity
    df_idx = df.set_index("CRN")
    assert df_idx.loc[101, "Room"] == "S"
    assert df_idx.loc[102, "Room"] == "L"
    assert df_idx.loc[103, "Room"] == "L"
    assert df["Valid"].all()


def test_no_room_large_enough_marks_invalid():
    census = pd.DataFrame({
        "CRN": [1],
        "course_ref": ["BIG"],
        "num_students": [1000]
    })
    enrollment = pd.DataFrame(columns=["student_id", "CRN"])
    rooms = pd.DataFrame({
        "room_name": ["A", "B"],
        "capacity": [100, 200]
    })
    g, df = run_scheduler(census, enrollment, rooms)
    assert len(df) == 1
    assert df.iloc[0]["Valid"] == False


def test_overlap_graph_edge_count_expected():
    # Student X in [1,2,3] => edges among (1,2),(1,3),(2,3) => 3 edges
    census = pd.DataFrame({
        "CRN": [1, 2, 3],
        "course_ref": ["A", "B", "C"],
        "num_students": [10, 10, 10]
    })
    enrollment = pd.DataFrame({
        "student_id": [999, 999, 999],
        "CRN": [1, 2, 3]
    })
    rooms = pd.DataFrame({"room_name": ["R"], "capacity": [100]})

    g = DSATURExamGraph(census, enrollment, rooms)
    g.build_graph()
    assert len(g.G.edges) == 3  # complete graph K3


def test_dsatur_uses_leq_colors_than_largest_first_on_dense_graph():
    # Dense graph: triangle + extra connections; DSATUR should be <= largest_first
    census = pd.DataFrame({
        "CRN": [1, 2, 3, 4],
        "course_ref": ["A", "B", "C", "D"],
        "num_students": [10, 10, 10, 10]
    })
    # Make a clique K4 via enrollment patterns: every student in multiple courses
    enrollment = pd.DataFrame({
        "student_id": [1,1,1,1, 2,2,2,2, 3,3,3,3, 4,4,4,4],
        "CRN":       [1,2,3,4, 1,2,3,4, 1,2,3,4, 1,2,3,4]
    })
    rooms = pd.DataFrame({"room_name": ["R1","R2","R3","R4"], "capacity":[50,50,50,50]})

    g = DSATURExamGraph(census, enrollment, rooms)
    g.build_graph()
    dsatur_colors = nx.coloring.greedy_color(g.G, strategy="DSATUR")
    largest_first = nx.coloring.greedy_color(g.G, strategy="largest_first")

    # Count distinct colors assigned
    dsatur_k = len(set(dsatur_colors.values()))
    lf_k = len(set(largest_first.values()))
    assert dsatur_k <= lf_k


def test_deterministic_results_on_same_input():
    # Run twice; assignments should be identical (given deterministic sorting)
    census = pd.DataFrame({
        "CRN": [11, 12, 13],
        "course_ref": ["A", "B", "C"],
        "num_students": [30, 20, 10]
    })
    # Make a chain: 11-12-13 via student shares
    enrollment = pd.DataFrame({
        "student_id": [1, 1, 2, 2],
        "CRN": [11, 12, 12, 13]
    })
    rooms = pd.DataFrame({
        "room_name": ["X", "Y", "Z"],
        "capacity": [100, 50, 50]
    })

    g1, df1 = run_scheduler(copy.deepcopy(census), copy.deepcopy(enrollment), copy.deepcopy(rooms))
    g2, df2 = run_scheduler(copy.deepcopy(census), copy.deepcopy(enrollment), copy.deepcopy(rooms))

    assert g1.assignment == g2.assignment
    pd.testing.assert_frame_equal(df1.sort_values(df1.columns.tolist()).reset_index(drop=True),
                                  df2.sort_values(df2.columns.tolist()).reset_index(drop=True))


def test_spread_across_many_slots_reduces_room_pressure():
    # 6 large courses, 3 big rooms. With many slots available, the algorithm should keep most Valid.
    census = pd.DataFrame({
        "CRN": [101,102,103,104,105,106],
        "course_ref": ["C1","C2","C3","C4","C5","C6"],
        "num_students": [240,230,220,210,200,190]
    })
    # No shared students; emphasis is room fitting across blocks
    enrollment = pd.DataFrame(columns=["student_id","CRN"])
    rooms = pd.DataFrame({
        "room_name": ["L1","L2","L3"], 
        "capacity": [250, 250, 250]
    })

    g, df = run_scheduler(census, enrollment, rooms, max_days=7)
    # With 35 slots available, expect almost all valid
    invalid = (~df["Valid"]).sum()
    assert invalid <= 1
