import pandas as pd
import networkx as nx
from itertools import combinations
from collections import defaultdict, Counter

class DSATURExamGraph:
    """
    DSATUR-based exam scheduler.

    Inputs (must be cleaned beforehand):
      census:      DataFrame with columns -> CRN, course_ref, num_students
      enrollment:  DataFrame with columns -> student_id, CRN
      classrooms:  DataFrame with columns -> room_name, capacity (int)
    """

    def __init__(self, census: pd.DataFrame, enrollment: pd.DataFrame, classrooms: pd.DataFrame):
        self.census = census.copy()
        self.enrollment = enrollment.copy()
        self.classrooms = classrooms.copy()

        self.G = nx.Graph()                 # potential-overlap graph
        self.colors = {}                    # CRN -> dsatur color (int)
        self.assignment = {}                # CRN -> (day, block)
        self.block_load = defaultdict(int)  # (day, block) -> number of exams

        # keep these at top of __init__
        self.block_exam_count = defaultdict(int)   # (day, block) -> #exams placed
        self.block_seat_load  = defaultdict(int)   # (day, block) -> sum of class sizes


        # 7 days (Mon..Sun) × 5 blocks/day
        self.exam_blocks = [(d, b) for d in range(7) for b in range(5)]

        # precompute students per course
        if len(self.enrollment) > 0:
            self.students_by_crn = (
                self.enrollment.groupby("CRN")["student_id"].apply(set).to_dict()
            )
        else:
            self.students_by_crn = {}

        # labels
        self.day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        self.block_times = {
            0: "9:00–11:00",
            1: "11:30–1:30",
            2: "2:00–4:00",
            3: "4:30–6:30",
            4: "7:00–9:00",
        }

        # diagnostics
        self.unplaced_reason_counts = {}   # CRN -> {reason: count}
        self.fallback_courses = set()      # CRNs that needed fallback

    # ---------------------------------------------------------------------
    # Build graph of potential overlaps (shared students add an edge)
    def build_graph(self):
        for _, row in self.census.iterrows():
            size = row.get("num_students", 0)
            size = int(size) if pd.notna(size) else 0
            self.G.add_node(
                row["CRN"],
                course_ref=row.get("course_ref", ""),
                size=size,
            )

        crn_set = set(self.census["CRN"].unique())
        for _, grp in self.enrollment.groupby("student_id"):
            crns = [c for c in grp["CRN"].tolist() if c in crn_set]
            for a, b in combinations(crns, 2):
                self.G.add_edge(a, b, conflict="student")

    # ---------------------------------------------------------------------
    # DSATUR base coloring (time-slot colors, not yet mapped to days/blocks)
    def dsatur_color(self):
        if self.G.number_of_nodes() == 0:
            raise RuntimeError("Call build_graph() first.")
        # NetworkX DSATUR heuristic
        self.colors = nx.coloring.greedy_color(self.G, strategy="DSATUR")
        return self.colors

    # ---------------------------------------------------------------------
    # Helper: can a student take this (day, block)?
    def _check_student_slot(self, student_sched, sid, day, block, max_per_day, avoid_back_to_back):
        todays = [b for d, b in student_sched[sid] if d == day]
        if len(todays) >= max_per_day:
            return False, "too_many_day"
        if block in todays:
            return False, "double_book"
        if avoid_back_to_back and (block - 1 in todays or block + 1 in todays):
            return False, "back_to_back"
        return True, None

    # ---------------------------------------------------------------------
    # Map DSATUR colors -> (day, block) with constraint-aware placement
    def dsatur_schedule(self, max_per_day: int = 3, avoid_back_to_back: bool = True,
                        rotate_start: bool = True, max_days: int = 7):
        if not self.colors:
            raise RuntimeError("Run dsatur_color() before dsatur_schedule().")

        usable_blocks = [(d, b) for (d, b) in self.exam_blocks if d < max_days]
        total_slots = len(usable_blocks)

        # group CRNs by DSATUR color
        color_to_crns = defaultdict(list)
        for crn, c in self.colors.items():
            color_to_crns[c].append(crn)

        # sort courses within each color (largest first)
        for c in color_to_crns:
            color_to_crns[c].sort(key=lambda crn: int(self.G.nodes[crn].get("size", 0)), reverse=True)

        # order colors by total load (heavier colors first)
        ordered_colors = sorted(
            color_to_crns.keys(),
            key=lambda c: sum(int(self.G.nodes[crn].get("size", 0)) for crn in color_to_crns[c]),
            reverse=True
        )

        student_sched = defaultdict(list)
        start_index = 0

        for ci, color in enumerate(ordered_colors):
            # start attempt block for this color
            # base_idx = (start_index + ci) % total_slots if rotate_start else (ci % total_slots)

            for crn in color_to_crns[color]:
                placed = False
                reason_counter = Counter()

                # try sequential slots, starting from base_idx
                # for step in range(total_slots):
                #     idx = (base_idx + step) % total_slots
                #     day, block = usable_blocks[idx]

                #     ok = True
                #     for sid in self.students_by_crn.get(crn, ()):
                #         ok_one, reason = self._check_student_slot(student_sched, sid, day, block, max_per_day, avoid_back_to_back)
                #         if not ok_one:
                #             ok = False
                #             reason_counter[reason] += 1
                #             break

                #     if ok:
                #         self.assignment[crn] = (day, block)
                #         for sid in self.students_by_crn.get(crn, ()):
                #             student_sched[sid].append((day, block))
                #         self.block_load[(day, block)] += 1
                #         placed = True
                #         break

                candidates = []
                for idx, (day, block) in enumerate(usable_blocks):
                    ok = True
                    for sid in self.students_by_crn.get(crn, ()):
                        ok_one, reason = self._check_student_slot(student_sched, sid, day, block,
                                                                  max_per_day, avoid_back_to_back)
                        if not ok_one:
                            ok = False
                            reason_counter[reason] += 1
                            break
                    if ok:
                        # heuristic: prefer the least loaded slot by seats, then by exam count
                        load_key = (self.block_seat_load[(day, block)], self.block_exam_count[(day, block)])
                        candidates.append((load_key, day, block))

                if candidates:
                    _, day, block = min(candidates)  # pick the least-loaded valid slot
                    self.assignment[crn] = (day, block)
                    for sid in self.students_by_crn.get(crn, ()):
                        student_sched[sid].append((day, block))
                    self.block_load[(day, block)] += 1
                    self.block_exam_count[(day, block)] += 1
                    self.block_seat_load[(day, block)]  += int(self.G.nodes[crn].get("size", 0))
                    placed = True
                else:
                    # fallback unchanged
                    day, block = usable_blocks[0]
                    self.assignment[crn] = (day, block)
                    for sid in self.students_by_crn.get(crn, ()):
                        student_sched[sid].append((day, block))
                    self.block_load[(day, block)] += 1
                    self.block_exam_count[(day, block)] += 1
                    self.block_seat_load[(day, block)]  += int(self.G.nodes[crn].get("size", 0))
                    self.fallback_courses.add(crn)
                    self.unplaced_reason_counts[crn] = dict(reason_counter)



        return self.assignment

    # ---------------------------------------------------------------------
    # Assign rooms by best fit, avoid reusing a room in same (day, block)
    def assign_rooms(self) -> pd.DataFrame:
        if not self.assignment:
            raise RuntimeError("Run dsatur_schedule() before assign_rooms().")

        used_rooms = defaultdict(set)
        rooms_asc = self.classrooms.sort_values("capacity").reset_index(drop=True)
        rooms_desc = rooms_asc.iloc[::-1].reset_index(drop=True)

        rows = []
        for crn, (day, block) in self.assignment.items():
            attrs = self.G.nodes[crn]
            size = int(attrs.get("size", 0))

            fit_mask = (rooms_asc["capacity"] >= size) & (~rooms_asc["room_name"].isin(used_rooms[(day, block)]))
            candidate = rooms_asc[fit_mask].head(1)

            valid = True
            if candidate.empty:
                free_mask = ~rooms_desc["room_name"].isin(used_rooms[(day, block)])
                fallback = rooms_desc[free_mask].head(1)
                if fallback.empty:
                    fallback = rooms_desc.head(1)
                candidate = fallback
                valid = int(candidate.iloc[0]["capacity"]) >= size

            room = candidate.iloc[0]
            used_rooms[(day, block)].add(room["room_name"])

            rows.append({
                "CRN": crn,
                "Course": attrs.get("course_ref", ""),
                "Day": self.day_names[day],
                "Block": f"{block} ({self.block_times[block]})",
                "Room": room["room_name"],
                "Capacity": int(room["capacity"]),
                "Size": size,
                "Valid": valid,
            })

        df = pd.DataFrame(rows)
        invalid = (~df["Valid"]).sum()
        print(f"Room assignment: {len(df)-invalid} valid, {invalid} invalid.")
        return df

    # ---------------------------------------------------------------------
    def fail_report(self) -> pd.DataFrame:
        cols = ["CRN", "Course", "Size", "reasons"]
        if not self.fallback_courses:
            return pd.DataFrame(columns=cols)

        rows = []
        for crn in sorted(self.fallback_courses):
            nd = self.G.nodes.get(crn, {})
            rows.append({
                "CRN": crn,
                "Course": nd.get("course_ref", ""),
                "Size": int(nd.get("size", 0)) if pd.notna(nd.get("size", 0)) else 0,
                "reasons": self.unplaced_reason_counts.get(crn, {}),
            })
        return pd.DataFrame(rows, columns=cols).sort_values("Size", ascending=False, ignore_index=True)

    # ---------------------------------------------------------------------
    def count_schedule_conflicts(self, max_per_day: int = 3, check_back_to_back: bool = True):
        if not self.assignment:
            raise RuntimeError("Run dsatur_schedule() before counting conflicts.")

        total = 0
        details = defaultdict(list)
        rows = []

        for sid, grp in self.enrollment.groupby("student_id"):
            slots = [self.assignment.get(crn) for crn in grp["CRN"] if crn in self.assignment]
            if not slots:
                continue

            by_day = defaultdict(list)
            for d, b in slots:
                by_day[d].append(b)

            for day, blocks in by_day.items():
                blocks.sort()

                if len(blocks) > max_per_day:
                    total += 1
                    details[sid].append(f"{self.day_names[day]}: >{max_per_day} exams")
                    rows.append({"student_id": sid, "day": self.day_names[day], "conflict_type": f">{max_per_day}_per_day", "blocks": blocks})

                if len(blocks) != len(set(blocks)):
                    total += 1
                    details[sid].append(f"{self.day_names[day]}: double_book")
                    rows.append({"student_id": sid, "day": self.day_names[day], "conflict_type": "double_book", "blocks": blocks})

                if check_back_to_back and any(blocks[i] == blocks[i-1] + 1 for i in range(1, len(blocks))):
                    total += 1
                    details[sid].append(f"{self.day_names[day]}: back_to_back")
                    rows.append({"student_id": sid, "day": self.day_names[day], "conflict_type": "back_to_back", "blocks": blocks})

        breakdown_df = pd.DataFrame(rows)
        return total, details, breakdown_df

    # ---------------------------------------------------------------------
    def summary(self) -> dict:
        potential_overlaps = len(self.G.edges)
        real_conflicts = 0
        if self.assignment:
            real_conflicts, _, _ = self.count_schedule_conflicts()

        slots_used = len({self.assignment[c] for c in self.assignment}) if self.assignment else 0

        return {
            "num_classes": len(self.G.nodes),
            "num_students": self.enrollment["student_id"].nunique(),
            "potential_overlaps": potential_overlaps,
            "real_conflicts": real_conflicts,
            "num_rooms": len(self.classrooms),
            "slots_used": slots_used,
        }