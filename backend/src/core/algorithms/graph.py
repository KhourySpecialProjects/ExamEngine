import os
import pandas as pd
import networkx as nx

class ExamGraph:
    def __init__(self, census_path=None, classrooms_path=None, enrollment_path=None):
        # Resolve project root (one level up from Backend/)
        base_dir = os.path.dirname(os.path.dirname(__file__))
        data_dir = os.path.join(base_dir, "Data")

        # Default to Data/ folder if no paths given
        census_path = census_path or os.path.join(data_dir, "DB_ClassCensus.csv")
        classrooms_path = classrooms_path or os.path.join(data_dir, "DB_Classrooms.csv")
        enrollment_path = enrollment_path or os.path.join(data_dir, "DB_Enrollment.csv")

        # Load CSVs
        self.class_census = pd.read_csv(census_path)
        self.classrooms = pd.read_csv(classrooms_path)
        self.enrollment = pd.read_csv(enrollment_path)

        print("ClassCensus columns:", self.class_census.columns.tolist())
        print("Classrooms columns:", self.classrooms.columns.tolist())
        print("Enrollment columns:", self.enrollment.columns.tolist())

        self.G = nx.Graph()
        self.coloring = {}

    def build_graph(self):
        """Build conflict graph: nodes = courses, edges = shared students"""
        for _, row in self.class_census.iterrows():
            self.G.add_node(
                row["course_id"],
                size=row["num_students"]
            )

        for student, group in self.enrollment.groupby("student_id"):
            courses = group["course_id"].tolist()
            for i in range(len(courses)):
                for j in range(i + 1, len(courses)):
                    self.G.add_edge(courses[i], courses[j])

    def run_coloring(self, strategy="largest_first"):
        """Color the graph using NetworkX greedy coloring"""
        self.coloring = nx.coloring.greedy_color(self.G, strategy=strategy)
        return self.coloring

    def validate_room_capacity(self):
        """Check if course fits in assigned room"""
        issues = []
        for course, slot in self.coloring.items():
            course_size = self.G.nodes[course]["size"]

            room_idx = slot % len(self.classrooms)
            room = self.classrooms.iloc[room_idx]

            if course_size > room["capacity"]:
                issues.append(
                    f"{course} (size {course_size}) exceeds room {room['room_id']} (capacity {room['capacity']})"
                )
        return issues

    def student_exam_load(self, max_per_day=3):
        """Compute exams per student per day (simplified)"""
        load = self.enrollment.groupby("student_id")["course_id"].count()
        overloaded = load[load > max_per_day]
        return overloaded

    def summary(self):
        """Return summary stats for frontend"""
        return {
            "num_classes": len(self.G.nodes),
            "num_students": self.enrollment["student_id"].nunique(),
            "num_conflicts": len(self.G.edges),
            "num_rooms": len(self.classrooms),
        }


# Debug run
if __name__ == "__main__":
    backend = ExamGraph()  # defaults to Data/ folder
    backend.build_graph()
    backend.run_coloring()
    print(backend.summary())
    print("Room issues:", backend.validate_room_capacity())
    print("Overloaded students:", backend.student_exam_load())
