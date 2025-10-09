import pandas as pd
from backend.src.algorithms.dsatur_scheduler import DSATURExamGraph

def test_dsatur_algorithm_basic():
    census = pd.DataFrame({
        "CRN": [1, 2],
        "course_ref": ["CS101", "CS102"],
        "num_students": [30, 25]
    })
    enrollment = pd.DataFrame({
        "student_id": [1, 1, 2, 3],
        "CRN": [1, 2, 1, 2]
    })
    classrooms = pd.DataFrame({
        "room_name": ["A", "B"],
        "capacity": [40, 30]
    })

    g = DSATURExamGraph(census, enrollment, classrooms)
    g.build_graph()
    g.dsatur_color()
    g.dsatur_schedule()
    df = g.assign_rooms()

    assert len(df) == 2
    assert df["Valid"].all()
    assert g.count_schedule_conflicts()[0] == 0
