import streamlit as st
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
import plotly.express as px
import os

st.set_page_config(page_title="Exam Scheduler", layout="wide")
st.title("📅 Exam Scheduler Validator")

# Sidebar
st.sidebar.header("⚙️ Settings")
alg_choice = st.sidebar.selectbox(
    "Select Coloring Algorithm", 
    ["greedy", "largest_first", "random_sequential"]
)
room_check = st.sidebar.checkbox("Validate room capacity", True)
load_check = st.sidebar.checkbox("Validate ≤3 exams/day", False)

# --- Safe path handling ---

base = os.path.dirname(__file__)   # path to Frontend/
data_dir = os.path.join(base, "..", "Data")  # go up one level, then into Data

class_census = pd.read_csv(os.path.join(data_dir, "DB_ClassCensus.csv"))
classrooms   = pd.read_csv(os.path.join(data_dir, "DB_Classrooms.csv"))
enrollment   = pd.read_csv(os.path.join(data_dir, "DB_Enrollment.csv"))


# --- Build Graph ---
G = nx.Graph()
for _, row in class_census.iterrows():
    G.add_node(row["course_id"], size=row["num_students"])

for student, group in enrollment.groupby("student_id"):
    courses = group["course_id"].tolist()
    for i in range(len(courses)):
        for j in range(i+1, len(courses)):
            G.add_edge(courses[i], courses[j])

# --- Run Coloring ---
coloring = nx.coloring.greedy_color(G, strategy=alg_choice)

# --- KPI Cards ---
col1, col2, col3, col4 = st.columns(4)
col1.metric("📘 Classes", len(G.nodes))
col2.metric("👩‍🎓 Students", enrollment["student_id"].nunique())
col3.metric("⚡ Conflicts", len(G.edges))
col4.metric("🏫 Rooms", len(classrooms))

# --- Data Preview ---
with st.expander("📊 Class Census Data"):
    st.dataframe(class_census)
with st.expander("🏫 Classroom Data"):
    st.dataframe(classrooms)
with st.expander("👥 Enrollment Data"):
    st.dataframe(enrollment.head(500))  # limit for performance

# --- Schedule Assignment Table ---
schedule_df = pd.DataFrame([
    {"Course": course, "Exam Slot": coloring[course]}
    for course in G.nodes
])
st.subheader("🗂️ Assigned Schedule")
st.dataframe(schedule_df)

# --- Graph Visualization (subset) ---
st.subheader("📈 Conflict Graph (Sample)")
subset_nodes = list(G.nodes)[:30]  # preview first 30
H = G.subgraph(subset_nodes)
pos = nx.spring_layout(H, seed=42)
plt.figure(figsize=(8,6))
nx.draw(
    H, pos, with_labels=True, node_size=500,
    node_color=[coloring.get(n,0) for n in H.nodes], cmap=plt.cm.Set3
)
st.pyplot(plt)

# --- Student Load Heatmap ---
st.subheader("📊 Student Exam Load Distribution")
student_counts = enrollment.groupby("student_id")["course_id"].count()
fig = px.histogram(student_counts, nbins=10, title="Exams per Student")
st.plotly_chart(fig, use_container_width=True)
