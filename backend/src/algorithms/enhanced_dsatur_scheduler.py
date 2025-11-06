from collections import defaultdict
from itertools import combinations

import networkx as nx
import pandas as pd


class DSATURExamGraph:
    """
    DSATUR-based exam scheduler

    All exams are ALWAYS placed, even if conflicts occur. Conflicts are tracked and reported
    but do not prevent scheduling.

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

    # ---------- normalization ----------
    @staticmethod
    def _normalize_inputs(census, enrollment, classrooms):
        c = census.copy()
        e = enrollment.copy()
        r = classrooms.copy()

        # Rename to canonical columns
        c = c.rename(columns={"CourseID": "course_ref"})
        e = e.rename(
            columns={"Student_PIDM": "student_id", "Instructor Name": "instructor_name"}
        )

        # Keep only required columns (ignore extras)
        need_c = ["CRN", "course_ref", "num_students"]
        need_e = ["student_id", "CRN", "instructor_name"]
        need_r = ["room_name", "capacity"]

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

        # Clean CRNs to string without ".0"
        def clean_crn(v):
            try:
                if pd.isna(v):
                    return None
                return str(int(float(v))).strip()
            except Exception:
                return str(v).strip()

        c["CRN"] = c["CRN"].apply(clean_crn)
        e["CRN"] = e["CRN"].apply(clean_crn)

        # Types
        c["num_students"] = (
            pd.to_numeric(c["num_students"], errors="coerce").fillna(0).astype(int)
        )
        e["student_id"] = e["student_id"].astype(str)
        e["instructor_name"] = e["instructor_name"].fillna("").astype(str).str.strip()
        r["capacity"] = (
            pd.to_numeric(r["capacity"], errors="coerce").fillna(0).astype(int)
        )

        # Filter empties & dedupe enrollment to prevent false collisions
        c = c.dropna(subset=["CRN"])
        e = e.dropna(subset=["CRN", "student_id"])
        e = e.drop_duplicates(subset=["student_id", "CRN"]).copy()

        return c, e, r

    def __init__(
        self,
        census: pd.DataFrame,
        enrollment: pd.DataFrame,
        classrooms: pd.DataFrame,
        weight_large_late: int = 1,
        weight_b2b_student: int = 6,
        weight_b2b_instructor: int = 2,
        max_student_per_day: int = 2,
        max_instructor_per_day: int = 2,
    ):
        self.census, self.enrollment, self.classrooms = self._normalize_inputs(
            census, enrollment, classrooms
        )

        # Keep only CRNs that exist in census
        crn_census = set(self.census["CRN"].unique())
        self.enrollment = self.enrollment[
            self.enrollment["CRN"].isin(crn_census)
        ].copy()

        # Soft weights
        self.weight_large_late = int(weight_large_late)
        self.weight_b2b_student = int(weight_b2b_student)
        self.weight_b2b_instructor = int(weight_b2b_instructor)
        self.max_student_per_day = int(max_student_per_day)
        self.max_instructor_per_day = int(max_instructor_per_day)

        # Core structures
        self.G = nx.Graph()
        self.colors = {}  # CRN -> DSATUR color
        self.assignment = {}  # CRN -> (day, block)
        self.unassigned = set()  # CRNs we could not place without breaking hard rules
        self.block_exam_count = defaultdict(int)
        self.block_seat_load = defaultdict(int)
        self.slot_to_crns = defaultdict(list)  # (day, block) -> [crn1, crn2, ...]

        # Time grid
        self.exam_blocks = [(d, b) for d in range(7) for b in range(5)]
        self.day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
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

        # Caches built later
        self.students_by_crn = {}  # CRN -> set(student_id)
        self.instructors_by_crn = {}  # CRN -> set(instructor_name)

        # Track instructor assignments persistently
        self.instructor_sched = defaultdict(list)  # instructor_name -> [(day, block)]

        # Diagnostics
        self.fallback_courses = set()  # logically impossible (no legal slot)
        self.unplaced_reason_counts = {}  # CRN -> {reason: count}

        # Conflict tracking (for reporting, not blocking)
        self.conflicts = []  # List of conflict records: (type, student_id/instructor_name, day, block, crn)

        # Post-schedule reports
        self.student_soft_violations = pd.DataFrame()
        self.instructor_soft_violations = pd.DataFrame()
        self.large_courses_not_early = pd.DataFrame()

    # ---------- graph build ----------
    def build_graph(self):
        # Nodes
        for _, row in self.census.iterrows():
            self.G.add_node(
                row["CRN"],
                course_ref=row.get("course_ref", ""),
                size=int(row.get("num_students", 0) or 0),
            )

        # Students per CRN
        self.students_by_crn = (
            self.enrollment.groupby("CRN")["student_id"].apply(set).to_dict()
            if not self.enrollment.empty
            else {}
        )

        # Instructors per CRN (collect all names for safety)
        tmp = (
            self.enrollment[self.enrollment["instructor_name"] != ""]
            .groupby("CRN")["instructor_name"]
            .apply(lambda s: {x for x in s if x})
        )
        self.instructors_by_crn = tmp.to_dict()

        crn_set = set(self.census["CRN"])

        # Edges: shared students
        for _, grp in self.enrollment.groupby("student_id"):
            crns = [c for c in grp["CRN"].tolist() if c in crn_set]
            for a, b in combinations(crns, 2):
                self.G.add_edge(a, b, conflict="student")

        # Edges: shared instructors
        instr_to_crns = defaultdict(list)
        for crn, instrs in self.instructors_by_crn.items():
            for instr in instrs:
                instr_to_crns[instr].append(crn)
        for crns in instr_to_crns.values():
            if len(crns) > 1:
                for a, b in combinations([c for c in crns if c in crn_set], 2):
                    if self.G.has_edge(a, b):
                        self.G[a][b]["conflict"] = "student|instructor"
                    else:
                        self.G.add_edge(a, b, conflict="instructor")

    def dsatur_color(self):
        if self.G.number_of_nodes() == 0:
            raise RuntimeError("Call build_graph() first.")
        self.colors = nx.coloring.greedy_color(self.G, strategy="DSATUR")
        return self.colors

    # ---------- constraints ----------
    def _check_conflicts(self, student_sched, instr_sched, crn, day, block):
        """
        Check for conflicts (but don't block placement).
        Returns list of conflict tuples: (type, entity_id, day, block, crn, conflicting_crn_or_list)
        Types: 'student_double_book', 'student_gt_max_per_day', 'instructor_double_book', 'instructor_gt_max_per_day'
        """
        conflicts = []

        # Check student conflicts
        for sid in self.students_by_crn.get(crn, ()):
            # Use .get() to handle case where student not in schedule yet
            student_slots = student_sched.get(sid, [])
            if (day, block) in student_slots:
                # Find which CRN is already scheduled at this slot for this student
                conflicting_crns = []
                for existing_crn, (d, b) in self.assignment.items():
                    if (d, b) == (day, block) and sid in self.students_by_crn.get(
                        existing_crn, ()
                    ):
                        conflicting_crns.append(existing_crn)
                # If no conflicting CRN found in assignment, check slot_to_crns
                if not conflicting_crns:
                    for existing_crn in self.slot_to_crns.get((day, block), []):
                        if sid in self.students_by_crn.get(existing_crn, ()):
                            conflicting_crns.append(existing_crn)
                conflicts.append(
                    (
                        "student_double_book",
                        sid,
                        day,
                        block,
                        crn,
                        conflicting_crns[0] if conflicting_crns else None,
                    )
                )

            todays = [b for d, b in student_slots if d == day]
            if len(todays) >= self.max_student_per_day:
                # Find all CRNs this student has on this day
                day_crns = []
                for existing_crn, (d, _b) in self.assignment.items():
                    if d == day and sid in self.students_by_crn.get(existing_crn, ()):
                        day_crns.append(existing_crn)
                conflicts.append(
                    ("student_gt_max_per_day", sid, day, block, crn, day_crns)
                )

        # Check instructor conflicts
        for instr in self.instructors_by_crn.get(crn, ()):
            # Use .get() to handle case where instructor not in schedule yet
            instr_slots = instr_sched.get(instr, [])
            if (day, block) in instr_slots:
                # Find which CRN is already scheduled at this slot for this instructor
                conflicting_crns = []
                for existing_crn, (d, b) in self.assignment.items():
                    if (d, b) == (day, block) and instr in self.instructors_by_crn.get(
                        existing_crn, ()
                    ):
                        conflicting_crns.append(existing_crn)
                # If no conflicting CRN found in assignment, check slot_to_crns
                if not conflicting_crns:
                    for existing_crn in self.slot_to_crns.get((day, block), []):
                        if instr in self.instructors_by_crn.get(existing_crn, ()):
                            conflicting_crns.append(existing_crn)
                conflicts.append(
                    (
                        "instructor_double_book",
                        instr,
                        day,
                        block,
                        crn,
                        conflicting_crns[0] if conflicting_crns else None,
                    )
                )

            todays_i = [b for d, b in instr_slots if d == day]
            if len(todays_i) >= self.max_instructor_per_day:
                # Find all CRNs this instructor has on this day
                day_crns = []
                for existing_crn, (d, _b) in self.assignment.items():
                    if d == day and instr in self.instructors_by_crn.get(
                        existing_crn, ()
                    ):
                        day_crns.append(existing_crn)
                conflicts.append(
                    ("instructor_gt_max_per_day", instr, day, block, crn, day_crns)
                )

        return conflicts

    def _soft_tuple(self, student_sched, instr_sched, crn, day, block):
        """
        Return weighted soft penalty tuple (lexicographically minimized):
          (large_late*wL, b2b_students*wS, b2b_instr*wI, seat_load, exam_count, day, block)
        """
        nd = self.G.nodes[crn]
        size = int(nd.get("size", 0) or 0)

        # 1) large early (Mon-Wed preferred -> day 0..2), later days penalized
        large_late = max(0, day - 2) if size >= 100 else 0

        # 2) back-to-back students
        b2b_students = 0
        for sid in self.students_by_crn.get(crn, ()):
            todays = [b for d, b in student_sched[sid] if d == day]
            if (block - 1 in todays) or (block + 1 in todays):
                b2b_students += 1

        # 3) back-to-back instructors
        b2b_instr = 0
        for instr in self.instructors_by_crn.get(crn, ()):
            todays_i = [b for d, b in instr_sched[instr] if d == day]
            if (block - 1 in todays_i) or (block + 1 in todays_i):
                b2b_instr += 1

        # 4) Instructor load balancing: penalize days where instructor already has assignments
        # This helps distribute instructor workload evenly across days
        instr_load_penalty = 0
        for instr in self.instructors_by_crn.get(crn, ()):
            # Count how many exams this instructor already has on this day
            day_count = len([b for d, b in instr_sched[instr] if d == day])
            instr_load_penalty += day_count

        # tie-breakers
        seat_load = self.block_seat_load[(day, block)]
        exam_ct = self.block_exam_count[(day, block)]

        return (
            large_late * self.weight_large_late,
            b2b_students * self.weight_b2b_student,
            b2b_instr * self.weight_b2b_instructor,
            instr_load_penalty,  # Load balancing: prefer days with fewer instructor assignments
            seat_load,
            exam_ct,
            day,
            block,
        )

    # ---------- scheduling ----------
    def dsatur_schedule(self, max_days: int = 7):
        if not self.colors:
            raise RuntimeError("Run dsatur_color() before dsatur_schedule().")

        # Persist allowed slots and use them everywhere
        self.max_days = int(max_days)
        self.usable_blocks = [(d, b) for d in range(self.max_days) for b in range(5)]

        # group by color; place larger first within color
        color_to_crns = defaultdict(list)
        for crn, c in self.colors.items():
            color_to_crns[c].append(crn)
        for c in color_to_crns:
            color_to_crns[c].sort(
                key=lambda x: int(self.G.nodes[x].get("size", 0) or 0), reverse=True
            )

        # order colors by total seats
        ordered_colors = sorted(
            color_to_crns.keys(),
            key=lambda c: sum(
                int(self.G.nodes[x].get("size", 0) or 0) for x in color_to_crns[c]
            ),
            reverse=True,
        )

        # live occupancy for checks
        student_sched = defaultdict(list)  # sid -> [(day, block)]
        instr_sched = defaultdict(list)  # name -> [(day, block)]

        for color in ordered_colors:
            for crn in color_to_crns[color]:
                candidates = []

                # Evaluate all slots - always place, but track conflicts
                for day, block in self.usable_blocks:
                    # Check for conflicts (but don't block)
                    conflicts = self._check_conflicts(
                        student_sched, instr_sched, crn, day, block
                    )

                    # Calculate soft penalty tuple
                    soft_tuple = self._soft_tuple(
                        student_sched, instr_sched, crn, day, block
                    )

                    # Add to candidates - prioritize conflict avoidance heavily
                    # Conflicts should be the PRIMARY concern, not just a tie-breaker
                    conflict_count = len(conflicts)

                    # Create tuple with conflict_count as HIGH PRIORITY (first element)
                    # This ensures slots with fewer conflicts are always preferred
                    # Format: (conflict_count, large_late*wL, b2b_students*wS, b2b_instr*wI, instr_load, seat_load, exam_ct, day, block)
                    candidates.append(
                        (
                            (conflict_count,)
                            + soft_tuple,  # Conflicts first for high priority
                            day,
                            block,
                            conflicts,  # Store conflicts for this slot
                        )
                    )

                # Always choose best slot (even if it has conflicts)
                # Conflicts are now the primary factor, then soft preferences
                _, day, block, slot_conflicts = min(candidates, key=lambda x: x[0])

                # Track conflicts for this placement
                self.conflicts.extend(slot_conflicts)

                # commit - always place the exam
                self.assignment[crn] = (day, block)
                self.slot_to_crns[(day, block)].append(crn)  # Track CRNs at each slot
                for sid in self.students_by_crn.get(crn, ()):
                    student_sched[sid].append((day, block))
                for instr in self.instructors_by_crn.get(crn, ()):
                    instr_sched[instr].append((day, block))
                    # Track instructor assignments persistently
                    self.instructor_sched[instr].append((day, block))
                self.block_exam_count[(day, block)] += 1
                self.block_seat_load[(day, block)] += int(
                    self.G.nodes[crn].get("size", 0) or 0
                )

        # sanity guard: all within allowed days
        self._check_allowed_slots()
        return self.assignment

    # ---------- optional local repair pass ----------
    def reduce_back_to_backs(self, max_moves=200):
        """Try to reduce student back-to-backs while preserving all hard rules."""
        if not self.assignment:
            return 0

        moved = 0
        # Build quick maps and rebuild persistent instructor schedule
        student_sched = defaultdict(set)
        instr_sched = defaultdict(set)
        self.instructor_sched = defaultdict(list)  # Rebuild from assignment
        for crn, (d, b) in self.assignment.items():
            if crn in self.unassigned:
                continue
            for s in self.students_by_crn.get(crn, ()):
                student_sched[s].add((d, b))
            for i in self.instructors_by_crn.get(crn, ()):
                instr_sched[i].add((d, b))
                self.instructor_sched[i].append((d, b))

        # Identify offenders
        offenders = []
        for sid, slots in student_sched.items():
            by_day = defaultdict(list)
            for d, b in slots:
                by_day[d].append(b)
            for d, blks in by_day.items():
                blks.sort()
                if any(blks[i] == blks[i - 1] + 1 for i in range(1, len(blks))):
                    offenders.append((sid, d))

        # Use ONLY allowed blocks here
        allowed_blocks = list(self.usable_blocks)

        for sid, day in offenders:
            if moved >= max_moves:
                break
            # pick a CRN the student has on that day
            crns_today = [
                crn
                for crn, (d, _b) in self.assignment.items()
                if crn not in self.unassigned
                and (sid in self.students_by_crn.get(crn, ()))
                and d == day
            ]
            # move the smallest (less disruptive) first
            crns_today.sort(key=lambda c: int(self.G.nodes[c].get("size", 0) or 0))
            for crn in crns_today:
                cur_d, cur_b = self.assignment[crn]
                current = self._soft_tuple(
                    student_sched, instr_sched, crn, cur_d, cur_b
                )
                current_conflicts = self._check_conflicts(
                    student_sched, instr_sched, crn, cur_d, cur_b
                )
                current_conflict_count = len(current_conflicts)
                best = ((current_conflict_count,) + current, cur_d, cur_b)

                for d, b in allowed_blocks:  # <-- enforce allowed days/blocks
                    if (d, b) == (cur_d, cur_b):
                        continue
                    # Check conflicts but prefer moves with fewer conflicts
                    conflicts = self._check_conflicts(
                        student_sched, instr_sched, crn, d, b
                    )
                    conflict_count = len(conflicts)
                    cand = self._soft_tuple(student_sched, instr_sched, crn, d, b)
                    # Conflicts first for high priority
                    cand_with_conflicts = (conflict_count,) + cand
                    if cand_with_conflicts < best[0]:
                        best = (cand_with_conflicts, d, b)
                _best_tuple, new_d, new_b = best
                if (new_d, new_b) != (cur_d, cur_b):
                    # apply move
                    for s in self.students_by_crn.get(crn, ()):
                        student_sched[s].discard((cur_d, cur_b))
                        student_sched[s].add((new_d, new_b))
                    for i in self.instructors_by_crn.get(crn, ()):
                        instr_sched[i].discard((cur_d, cur_b))
                        instr_sched[i].add((new_d, new_b))
                        # Update persistent instructor schedule
                        if (cur_d, cur_b) in self.instructor_sched[i]:
                            self.instructor_sched[i].remove((cur_d, cur_b))
                        self.instructor_sched[i].append((new_d, new_b))
                    self.assignment[crn] = (new_d, new_b)
                    moved += 1
                    break

        # guard again after repairs
        self._check_allowed_slots()
        return moved

    # ---------- rooms ----------
    def assign_rooms(self) -> pd.DataFrame:
        if not self.assignment:
            raise RuntimeError("Run dsatur_schedule() before assign_rooms().")

        # quick guard
        self._check_allowed_slots()

        used = defaultdict(set)
        rooms_asc = self.classrooms.sort_values("capacity").reset_index(drop=True)
        rooms_desc = rooms_asc.iloc[::-1].reset_index(drop=True)

        rows = []
        for crn, (day, block) in self.assignment.items():
            if crn in self.unassigned:
                continue  # skip unplaced

            size = int(self.G.nodes[crn].get("size", 0) or 0)

            fit = rooms_asc[
                (rooms_asc["capacity"] >= size)
                & (~rooms_asc["room_name"].isin(used[(day, block)]))
            ].head(1)

            valid = True
            if fit.empty:
                free = rooms_desc[
                    ~rooms_desc["room_name"].isin(used[(day, block)])
                ].head(1)
                if free.empty:
                    free = rooms_desc.head(1)
                fit = free
                valid = int(fit.iloc[0]["capacity"]) >= size

            room = fit.iloc[0]
            used[(day, block)].add(room["room_name"])

            # Extract course_ref and ensure it's a clean string
            node_data = self.G.nodes[crn]
            course_ref = node_data.get("course_ref", "")
            # Ensure course_ref is a string, not a Series or other type
            if isinstance(course_ref, pd.Series):
                course_str = str(course_ref.iloc[0]) if len(course_ref) > 0 else ""
            else:
                course_str = str(course_ref) if course_ref is not None else ""

            rows.append(
                {
                    "CRN": crn,
                    "Course": course_str,
                    "Day": self.day_names[day],
                    "Block": f"{block} ({self.block_times[block]})",
                    "Room": room["room_name"],
                    "Capacity": int(room["capacity"]),
                    "Size": size,
                    "Valid": valid,
                    "Instructor": self.instructors_by_crn.get(crn, set()),
                }
            )

        df = pd.DataFrame(rows)
        self._compute_reports(df)
        return df

    # ---------- reports ----------
    def _compute_reports(self, df_schedule: pd.DataFrame):
        crn_to_dayblock = {
            crn: (self.day_names[d], b)
            for crn, (d, b) in self.assignment.items()
            if crn not in self.unassigned
        }

        # Students: (back-to-back) - note >2/day is hard, so you shouldn't see it here
        stu_rows = []
        for sid, grp in self.enrollment.groupby("student_id"):
            per_day = defaultdict(list)
            for crn in grp["CRN"]:
                if crn in crn_to_dayblock:
                    day, b = crn_to_dayblock[crn]
                    per_day[day].append(b)
            for day, blocks in per_day.items():
                blocks.sort()
                if any(blocks[i] == blocks[i - 1] + 1 for i in range(1, len(blocks))):
                    stu_rows.append(
                        {
                            "student_id": sid,
                            "violation": "back_to_back",
                            "day": day,
                            "blocks": blocks,
                        }
                    )
        self.student_soft_violations = pd.DataFrame(stu_rows)

        # Instructors: back-to-back
        instr_rows = []
        instr_slots = defaultdict(list)  # name -> [(day_str, block)]
        for crn, (d, b) in self.assignment.items():
            if crn in self.unassigned:
                continue
            for instr in self.instructors_by_crn.get(crn, ()):
                instr_slots[instr].append((self.day_names[d], b))

        for instr, slots in instr_slots.items():
            per_day = defaultdict(list)
            for day, b in slots:
                per_day[day].append(b)
            for day, blocks in per_day.items():
                blocks.sort()
                if any(blocks[i] == blocks[i - 1] + 1 for i in range(1, len(blocks))):
                    instr_rows.append(
                        {
                            "instructor_name": instr,
                            "violation": "back_to_back",
                            "day": day,
                            "blocks": blocks,
                        }
                    )
        self.instructor_soft_violations = pd.DataFrame(instr_rows)

        # Large courses not early (Thu-Sun)
        late_rows = []
        for crn, (d, b) in self.assignment.items():
            if crn in self.unassigned:
                continue
            size = int(self.G.nodes[crn].get("size", 0) or 0)
            if size >= 100 and d > 2:
                late_rows.append(
                    {
                        "CRN": crn,
                        "Course": self.G.nodes[crn].get("course_ref", ""),
                        "Size": size,
                        "Day": self.day_names[d],
                        "Block": f"{b} ({self.block_times[b]})",
                    }
                )
        self.large_courses_not_early = pd.DataFrame(late_rows)

    def summary(self) -> dict:
        # Count conflicts from tracked conflict list
        student_double_book = 0
        student_gt_max_per_day = 0
        instructor_double_book = 0
        instructor_gt_max_per_day = 0

        for conflict_tuple in self.conflicts:
            # Handle both old format (5 elements) and new format (6 elements)
            if len(conflict_tuple) == 5:
                conflict_type, entity_id, day, block, crn = conflict_tuple
                conflicting_info = None
            else:
                conflict_type, entity_id, day, block, crn, conflicting_info = (
                    conflict_tuple
                )

            if conflict_type == "student_double_book":
                student_double_book += 1
            elif conflict_type == "student_gt_max_per_day":
                student_gt_max_per_day += 1
            elif conflict_type == "instructor_double_book":
                instructor_double_book += 1
            elif conflict_type == "instructor_gt_max_per_day":
                instructor_gt_max_per_day += 1

        # Total hard conflicts (double-bookings + per-day violations)
        hard_student_conflicts = student_double_book + student_gt_max_per_day
        hard_instructor_conflicts = instructor_double_book + instructor_gt_max_per_day

        students_b2b = (
            0
            if self.student_soft_violations.empty
            else self.student_soft_violations["student_id"].nunique()
        )
        instr_b2b = (
            0
            if self.instructor_soft_violations.empty
            else self.instructor_soft_violations["instructor_name"].nunique()
        )

        return {
            "hard_student_conflicts": hard_student_conflicts,
            "hard_instructor_conflicts": hard_instructor_conflicts,
            "student_double_book": student_double_book,
            "student_gt_max_per_day": student_gt_max_per_day,
            "instructor_double_book": instructor_double_book,
            "instructor_gt_max_per_day": instructor_gt_max_per_day,
            "students_back_to_back": students_b2b,  # Warnings only
            "instructors_back_to_back": instr_b2b,  # Warnings only
            "large_courses_not_early": 0
            if self.large_courses_not_early.empty
            else len(self.large_courses_not_early),
            "num_classes": len(self.G.nodes),
            "num_students": self.enrollment["student_id"].nunique(),
            "num_rooms": len(self.classrooms),
            "slots_used": len(set(self.assignment.values())) if self.assignment else 0,
            "unplaced_exams": len(self.unassigned),
        }

    def fail_report(self) -> pd.DataFrame:
        """CRNs that could not be scheduled without breaking hard rules."""
        if not self.fallback_courses:
            return pd.DataFrame(columns=["CRN", "Course", "Size", "reasons"])
        rows = []
        for crn in sorted(self.fallback_courses):
            nd = self.G.nodes.get(crn, {})
            rows.append(
                {
                    "CRN": crn,
                    "Course": nd.get("course_ref", ""),
                    "Size": int(nd.get("size", 0) or 0),
                    "reasons": self.unplaced_reason_counts.get(crn, {}),
                }
            )
        return pd.DataFrame(rows).sort_values(
            "Size", ascending=False, ignore_index=True
        )

    # ---------- helper guard ----------
    def _check_allowed_slots(self):
        """Assert that all assignments are within the allowed day range."""
        illegal = [
            (crn, d, b) for crn, (d, b) in self.assignment.items() if d >= self.max_days
        ]
        if illegal:
            # If you prefer hard failure, raise. Otherwise, fix to first allowed slot.
            # raise AssertionError(f"Found assignments outside allowed days: {illegal[:10]}")
            for crn, _, _ in illegal:
                # move into first legal slot (keeps schedule valid)
                self.assignment[crn] = self.usable_blocks[0]


def export_student_schedule(
    g_backend,
    enrollment_df: pd.DataFrame,
    df_schedule: pd.DataFrame,
    base_name: str = "student_schedule",
    include_instructor: bool = True,
    add_blank_between_students: bool = False,
):
    """
    Creates a single CSV:
      - {base_name}_by_student_long.csv : one row per student-exam (chronological)

    Accepts enrollment columns in either style:
      - ['student_id','CRN','instructor_name']  (preferred)
      - ['Student_PIDM','CRN','Instructor Name'] (legacy)

    Expects:
      - g_backend.assignment: dict CRN -> (day_idx, block_idx)
        * If your scheduler exposes g_backend.unassigned (set of CRNs), these will be skipped.
      - df_schedule: columns ['CRN','Course','Day','Block','Room','Capacity','Size','Valid']
    """
    import re

    # --- helpers ---
    def clean_crn(v):
        try:
            if pd.isna(v):
                return None
            return str(int(float(v))).strip()  # handles 11310.0 -> "11310"
        except Exception:
            return str(v).strip()

    # --- normalize enrollment columns (rename legacy -> canonical) ---
    enroll = enrollment_df.copy()
    col_renames = {}
    if "Student_PIDM" in enroll.columns and "student_id" not in enroll.columns:
        col_renames["Student_PIDM"] = "student_id"
    if "Instructor Name" in enroll.columns and "instructor_name" not in enroll.columns:
        col_renames["Instructor Name"] = "instructor_name"
    if col_renames:
        enroll = enroll.rename(columns=col_renames)

    # ensure required columns exist now
    need_cols = {"student_id", "CRN"}
    missing = need_cols - set(enroll.columns)
    if missing:
        raise ValueError(
            f"enrollment_df is missing required columns after normalization: {sorted(missing)}"
        )

    # keep minimal columns, clean types
    keep_cols = ["student_id", "CRN"] + (
        ["instructor_name"] if "instructor_name" in enroll.columns else []
    )
    enroll = enroll.loc[:, keep_cols].copy()

    # types & cleaning
    enroll["student_id"] = enroll["student_id"].astype(str).str.strip()
    enroll["CRN"] = enroll["CRN"].apply(clean_crn)
    if "instructor_name" in enroll.columns:
        enroll["instructor_name"] = (
            enroll["instructor_name"].fillna("").astype(str).str.strip()
        )

    # drop empties / dupes
    enroll = enroll.dropna(subset=["student_id", "CRN"])
    enroll = enroll[enroll["CRN"] != ""]
    enroll = enroll.drop_duplicates(subset=["student_id", "CRN"])

    # --- instructor map: CRN -> semicolon-joined unique names (if requested) ---
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

    # --- schedule metadata (ensure CRN cleaned) ---
    sched = df_schedule.copy()
    if "CRN" not in sched.columns:
        raise ValueError("df_schedule must contain a 'CRN' column.")
    sched["CRN"] = sched["CRN"].apply(clean_crn)
    meta = sched.set_index("CRN").to_dict(orient="index")

    # --- optionally skip unassigned CRNs if backend provides it ---
    unassigned = set(getattr(g_backend, "unassigned", set()) or [])

    # --- build long rows ---
    long_rows = []

    # stable student order (string sort)
    for sid, grp in enroll.groupby("student_id", sort=True):
        items = []
        for raw_crn in grp["CRN"]:
            crn = clean_crn(raw_crn)
            if crn in unassigned:
                continue
            if crn in getattr(g_backend, "assignment", {}) and crn in meta:
                day_idx, block_idx = g_backend.assignment[crn]
                info = meta[crn]
                items.append((day_idx, block_idx, crn, info))

        # chronological per student
        items.sort(key=lambda x: (x[0], x[1]))

        # emit rows
        for i, (d, b, crn, info) in enumerate(items, 1):
            block_str = str(info.get("Block", ""))
            m = re.search(
                r"(\d+)", block_str
            )  # extract leading number if "2 (2:00-4:00)"
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

        if add_blank_between_students and items:
            # add a blank separator row (keeps columns consistent)
            keys = list(long_rows[-1].keys())
            long_rows.append(dict.fromkeys(keys, ""))

    # --- finalize dataframe & sort (unless blanks inserted) ---
    long_df = pd.DataFrame(long_rows)

    if not add_blank_between_students and not long_df.empty:
        sort_cols = [
            c
            for c in ["student_id", "Day_idx", "Block_num", "exam_num"]
            if c in long_df.columns
        ]
        long_df = long_df.sort_values(sort_cols, kind="mergesort")

    # --- save ---
    out_path = f"{base_name}_by_student_long.csv"
    long_df.to_csv(out_path, index=False)

    placed = int(long_df["CRN"].ne("").sum()) if not long_df.empty else 0
    print(f"SUCCESS: Saved {placed} exam records to {out_path}")
    if unassigned:
        print(
            f"WARNING: Skipped {len(unassigned)} unassigned CRNs (hard-rule placement impossible)."
        )

    return long_df
