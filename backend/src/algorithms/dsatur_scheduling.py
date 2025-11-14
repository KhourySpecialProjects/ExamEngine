"""
DSATUR Scheduling and Room Assignment Module

This module handles the scheduling phase of the DSATUR algorithm, including:
- Conflict detection and checking
- Time slot assignment based on graph colors
- Room assignment based on capacity
- Schedule optimization and repair
- Conflict reporting and statistics

The scheduling process assigns each course (CRN) to a specific (day, block) time slot,
then assigns appropriate rooms based on enrollment size and room capacity.
"""

from collections import defaultdict

import pandas as pd


class DSATURSchedulingMixin:
    """
    Mixin class containing scheduling, conflict checking, and room assignment methods.
    
    This mixin provides all the methods needed after graph coloring:
    - Conflict detection (student/instructor double-booking, max per day)
    - Soft constraint evaluation (back-to-back, large course placement)
    - Time slot assignment
    - Room assignment
    - Schedule optimization
    - Reporting and statistics
    """

    # ---------- conflict checking ----------
    def _check_conflicts(self, student_sched, instr_sched, crn, day, block):
        """
        Check for conflicts when placing a course at a specific time slot.
        
        Conflicts are detected but do NOT block placement - all exams are always placed.
        This method tracks conflicts for reporting purposes.
        
        Conflict types detected:
        - student_double_book: Student has another exam at the same (day, block)
        - student_gt_max_per_day: Student exceeds max exams per day limit
        - instructor_double_book: Instructor has another exam at the same (day, block)
        - instructor_gt_max_per_day: Instructor exceeds max exams per day limit
        
        Args:
            student_sched: Dictionary mapping student_id -> [(day, block), ...]
            instr_sched: Dictionary mapping instructor_name -> [(day, block), ...]
            crn: Course Reference Number to check
            day: Day index (0-6)
            block: Block index (0-4)
            
        Returns:
            List of conflict tuples: (type, entity_id, day, block, crn, conflicting_crn_or_list)
        """
        conflicts = []

        # Check student conflicts
        for sid in self.students_by_crn.get(crn, ()):
            # Use .get() to handle case where student not in schedule yet
            student_slots = student_sched.get(sid, [])
            if (day, block) in student_slots:
                # Find which CRN is already scheduled at this slot for this student
                # Use slot_to_crns first (O(1) lookup, then O(K) where K is small)
                conflicting_crns = []
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

            # Check for max per day violation
            # Count how many exams this student already has on this day
            todays = [b for d, b in student_slots if d == day]
            if len(todays) >= self.student_max_per_day:
                # Find all CRNs this student has on this day
                # Use slot_to_crns filtered by day (much faster than iterating all assignments)
                day_crns = []
                for block_idx in range(5):  # 5 blocks per day
                    for existing_crn in self.slot_to_crns.get((day, block_idx), []):
                        if sid in self.students_by_crn.get(existing_crn, ()):
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
                # Use slot_to_crns first (O(1) lookup, then O(K) where K is small)
                conflicting_crns = []
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

            # Check for max per day violation
            todays_i = [b for d, b in instr_slots if d == day]
            if len(todays_i) >= self.instructor_max_per_day:
                # Find all CRNs this instructor has on this day
                # Use slot_to_crns filtered by day (much faster than iterating all assignments)
                day_crns = []
                for block_idx in range(5):  # 5 blocks per day
                    for existing_crn in self.slot_to_crns.get((day, block_idx), []):
                        if instr in self.instructors_by_crn.get(existing_crn, ()):
                            day_crns.append(existing_crn)
                conflicts.append(
                    ("instructor_gt_max_per_day", instr, day, block, crn, day_crns)
                )

        return conflicts

    def _soft_tuple(self, student_sched, instr_sched, crn, day, block):
        """
        Calculate soft constraint penalty tuple for a time slot.
        
        Soft constraints are preferences that we try to minimize but don't block placement.
        The tuple is designed for lexicographic comparison (minimize in order):
        1. Large course late penalty (large courses prefer earlier days)
        2. Back-to-back student penalty (avoid consecutive blocks for students)
        3. Back-to-back instructor penalty (avoid consecutive blocks for instructors)
        4. Instructor load balancing (distribute instructor workload)
        5. Seat load (total students scheduled in this slot)
        6. Exam count (number of exams in this slot)
        7. Day and block (tie-breakers)
        
        Args:
            student_sched: Dictionary mapping student_id -> [(day, block), ...]
            instr_sched: Dictionary mapping instructor_name -> [(day, block), ...]
            crn: Course Reference Number
            day: Day index (0-6)
            block: Block index (0-4)
            
        Returns:
            Tuple of penalty values for lexicographic comparison
        """
        nd = self.G.nodes[crn]
        size = int(nd.get("size", 0) or 0)

        # 1) Large course early preference (Mon-Wed = days 0-2 preferred)
        # Courses with >=100 students should be scheduled earlier in the week
        large_late = max(0, day - 2) if size >= 100 else 0

        # 2) Back-to-back student penalty
        # Count how many students would have consecutive exam blocks
        b2b_students = 0
        for sid in self.students_by_crn.get(crn, ()):
            todays = [b for d, b in student_sched[sid] if d == day]
            # Check if this block is adjacent to any existing block for this student
            if (block - 1 in todays) or (block + 1 in todays):
                b2b_students += 1

        # 3) Back-to-back instructor penalty
        # Count how many instructors would have consecutive exam blocks
        b2b_instr = 0
        for instr in self.instructors_by_crn.get(crn, ()):
            todays_i = [b for d, b in instr_sched[instr] if d == day]
            if (block - 1 in todays_i) or (block + 1 in todays_i):
                b2b_instr += 1

        # 4) Instructor load balancing
        # Penalize days where instructor already has many assignments
        # This helps distribute instructor workload evenly across days
        instr_load_penalty = 0
        for instr in self.instructors_by_crn.get(crn, ()):
            # Count how many exams this instructor already has on this day
            day_count = len([b for d, b in instr_sched[instr] if d == day])
            instr_load_penalty += day_count

        # Tie-breakers: prefer slots with lower load
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

    # ---------- scheduling algorithm ----------
    def dsatur_schedule(self, max_days: int = 7, prioritize_large_courses: bool = False):
        """
        Assign courses to time slots based on DSATUR coloring.
        
        This is the core scheduling algorithm that:
        1. Groups courses by their DSATUR color (or sorts by size if prioritize_large_courses=True)
        2. Orders colors by total enrollment (largest first) OR processes by size
        3. For each course, evaluates all possible time slots
        4. Selects the slot with minimum conflicts and soft penalties
        5. Always places the exam (even if conflicts exist)
        
        The algorithm prioritizes:
        - Minimizing hard conflicts (double-booking, max per day)
        - Minimizing soft constraints (back-to-back, large course placement)
        - Balancing load across time slots
        
        Args:
            max_days: Maximum number of days to use for scheduling (default: 7)
            prioritize_large_courses: If True, schedule largest courses first regardless of color (default: False)
            
        Returns:
            Dictionary mapping CRN -> (day, block) assignment
            
        Raises:
            RuntimeError: If graph coloring hasn't been performed
        """
        if not self.colors:
            raise RuntimeError("Run dsatur_color() before dsatur_schedule().")

        # Set allowed time slots based on max_days
        # Each day has 5 blocks, so total slots = max_days * 5
        self.max_days = int(max_days)
        self.usable_blocks = [(d, b) for d in range(self.max_days) for b in range(5)]
        self.prioritize_large_courses = prioritize_large_courses

        # Track live schedule state as we place exams
        student_sched = defaultdict(list)  # sid -> [(day, block)]
        instr_sched = defaultdict(list)  # name -> [(day, block)]

        # Two scheduling modes:
        if prioritize_large_courses:
            # MODE 1: Prioritize large courses - ignore color groups, sort all courses by size
            # This ensures the largest courses get the best time slots first
            ordered_crns = sorted(
                self.colors.keys(),
                key=lambda crn: int(self.G.nodes[crn].get("size", 0) or 0),
                reverse=True,
            )
            
            # Process courses in size order (largest first)
            for crn in ordered_crns:
                candidates = []

                # Evaluate all possible time slots for this course
                for day, block in self.usable_blocks:
                    # Check for conflicts (but don't block placement)
                    conflicts = self._check_conflicts(
                        student_sched, instr_sched, crn, day, block
                    )

                    # Calculate soft penalty tuple
                    soft_tuple = self._soft_tuple(
                        student_sched, instr_sched, crn, day, block
                    )

                    # Build candidate tuple with conflict count as highest priority
                    # Format: (conflict_count, large_late*wL, b2b_students*wS, b2b_instr*wI, 
                    #          instr_load, seat_load, exam_ct, day, block)
                    conflict_count = len(conflicts)
                    candidates.append(
                        (
                            (conflict_count,)
                            + soft_tuple,  # Conflicts first for high priority
                            day,
                            block,
                            conflicts,  # Store conflicts for this slot
                        )
                    )

                # Select the best slot (minimum conflict count, then minimum soft penalties)
                # Always place the exam, even if all slots have conflicts
                _, day, block, slot_conflicts = min(candidates, key=lambda x: x[0])

                # Track conflicts for reporting
                self.conflicts.extend(slot_conflicts)

                # Commit the assignment
                self.assignment[crn] = (day, block)
                self.slot_to_crns[(day, block)].append(crn)  # Track CRNs at each slot
                
                # Update live schedule state
                for sid in self.students_by_crn.get(crn, ()):
                    student_sched[sid].append((day, block))
                for instr in self.instructors_by_crn.get(crn, ()):
                    instr_sched[instr].append((day, block))
                    # Track instructor assignments persistently
                    self.instructor_sched[instr].append((day, block))
                
                # Update slot load statistics
                self.block_exam_count[(day, block)] += 1
                self.block_seat_load[(day, block)] += int(
                    self.G.nodes[crn].get("size", 0) or 0
                )
        else:
            # MODE 2: Standard DSATUR - process by color groups
            # Group courses by their DSATUR color
            # Courses with the same color can potentially share time slots
            color_to_crns = defaultdict(list)
            for crn, c in self.colors.items():
                color_to_crns[c].append(crn)
            
            # Within each color group, sort by size (largest first)
            # This ensures large courses get priority in slot selection
            for c in color_to_crns:
                color_to_crns[c].sort(
                    key=lambda x: int(self.G.nodes[x].get("size", 0) or 0), reverse=True
                )

            # Order color groups by total enrollment (largest first)
            # Process color groups with more students first
            ordered_colors = sorted(
                color_to_crns.keys(),
                key=lambda c: sum(
                    int(self.G.nodes[x].get("size", 0) or 0) for x in color_to_crns[c]
                ),
                reverse=True,
            )

            # Process each color group in order
            for color in ordered_colors:
                # Process courses within this color group (largest first)
                for crn in color_to_crns[color]:
                    candidates = []

                    # Evaluate all possible time slots for this course
                    for day, block in self.usable_blocks:
                        # Check for conflicts (but don't block placement)
                        conflicts = self._check_conflicts(
                            student_sched, instr_sched, crn, day, block
                        )

                        # Calculate soft penalty tuple
                        soft_tuple = self._soft_tuple(
                            student_sched, instr_sched, crn, day, block
                        )

                        # Build candidate tuple with conflict count as highest priority
                        # Format: (conflict_count, large_late*wL, b2b_students*wS, b2b_instr*wI, 
                        #          instr_load, seat_load, exam_ct, day, block)
                        conflict_count = len(conflicts)
                        candidates.append(
                            (
                                (conflict_count,)
                                + soft_tuple,  # Conflicts first for high priority
                                day,
                                block,
                                conflicts,  # Store conflicts for this slot
                            )
                        )

                    # Select the best slot (minimum conflict count, then minimum soft penalties)
                    # Always place the exam, even if all slots have conflicts
                    _, day, block, slot_conflicts = min(candidates, key=lambda x: x[0])

                    # Track conflicts for reporting
                    self.conflicts.extend(slot_conflicts)

                    # Commit the assignment
                    self.assignment[crn] = (day, block)
                    self.slot_to_crns[(day, block)].append(crn)  # Track CRNs at each slot
                    
                    # Update live schedule state
                    for sid in self.students_by_crn.get(crn, ()):
                        student_sched[sid].append((day, block))
                    for instr in self.instructors_by_crn.get(crn, ()):
                        instr_sched[instr].append((day, block))
                        # Track instructor assignments persistently
                        self.instructor_sched[instr].append((day, block))
                    
                    # Update slot load statistics
                    self.block_exam_count[(day, block)] += 1
                    self.block_seat_load[(day, block)] += int(
                        self.G.nodes[crn].get("size", 0) or 0
                    )

        # Validate all assignments are within allowed day range
        self._check_allowed_slots()
        return self.assignment

    # ---------- schedule optimization ----------
    def reduce_back_to_backs(self, max_moves=200):
        """
        Attempt to reduce student back-to-back exam conflicts through local search.
        
        This is an optional optimization pass that tries to move exams to reduce
        the number of students with consecutive exam blocks, while preserving
        all hard constraints (no double-booking, max per day limits).
        
        The algorithm:
        1. Identifies students with back-to-back exams
        2. Tries moving one of their exams to a better slot
        3. Only accepts moves that reduce conflicts or soft penalties
        4. Stops after max_moves or when no improvements are found
        
        Args:
            max_moves: Maximum number of exam moves to attempt (default: 200)
            
        Returns:
            Number of exams successfully moved
        """
        if not self.assignment:
            return 0

        moved = 0
        
        # Rebuild schedule state from current assignments
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

        # Identify students with back-to-back exams
        offenders = []
        for sid, slots in student_sched.items():
            by_day = defaultdict(list)
            for d, b in slots:
                by_day[d].append(b)
            for d, blks in by_day.items():
                blks.sort()
                # Check if any consecutive blocks exist
                if any(blks[i] == blks[i - 1] + 1 for i in range(1, len(blks))):
                    offenders.append((sid, d))

        # Try to fix each offender
        allowed_blocks = list(self.usable_blocks)
        for sid, day in offenders:
            if moved >= max_moves:
                break
            
            # Get all courses this student has on the problematic day
            crns_today = [
                crn
                for crn, (d, _b) in self.assignment.items()
                if crn not in self.unassigned
                and (sid in self.students_by_crn.get(crn, ()))
                and d == day
            ]
            
            # Try moving the smallest course first (less disruptive)
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

                # Evaluate all alternative slots
                for d, b in allowed_blocks:
                    if (d, b) == (cur_d, cur_b):
                        continue
                    # Check conflicts and soft penalties for this alternative
                    conflicts = self._check_conflicts(
                        student_sched, instr_sched, crn, d, b
                    )
                    conflict_count = len(conflicts)
                    cand = self._soft_tuple(student_sched, instr_sched, crn, d, b)
                    cand_with_conflicts = (conflict_count,) + cand
                    
                    # Accept if this slot is better
                    if cand_with_conflicts < best[0]:
                        best = (cand_with_conflicts, d, b)
                
                _best_tuple, new_d, new_b = best
                
                # Apply the move if we found a better slot
                if (new_d, new_b) != (cur_d, cur_b):
                    # Update student schedule
                    for s in self.students_by_crn.get(crn, ()):
                        student_sched[s].discard((cur_d, cur_b))
                        student_sched[s].add((new_d, new_b))
                    
                    # Update instructor schedule
                    for i in self.instructors_by_crn.get(crn, ()):
                        instr_sched[i].discard((cur_d, cur_b))
                        instr_sched[i].add((new_d, new_b))
                        # Update persistent instructor schedule
                        if (cur_d, cur_b) in self.instructor_sched[i]:
                            self.instructor_sched[i].remove((cur_d, cur_b))
                        self.instructor_sched[i].append((new_d, new_b))
                    
                    # Update assignment
                    self.assignment[crn] = (new_d, new_b)
                    moved += 1
                    break

        # Validate assignments after repairs
        self._check_allowed_slots()
        return moved

    # ---------- room assignment ----------
    def assign_rooms(self) -> pd.DataFrame:
        """
        Assign rooms to scheduled exams based on capacity.
        
        For each scheduled exam, finds an appropriate room:
        1. Prefers rooms with capacity >= enrollment size
        2. Avoids double-booking rooms at the same time slot
        3. Falls back to largest available room if no perfect fit
        
        Args:
            None (uses self.assignment and self.classrooms)
            
        Returns:
            DataFrame with columns: CRN, Course, Day, Block, Room, Capacity, Size, Valid, Instructor
            
        Raises:
            RuntimeError: If scheduling hasn't been performed
        """
        if not self.assignment:
            raise RuntimeError("Run dsatur_schedule() before assign_rooms().")

        # Validate all assignments are within allowed day range
        self._check_allowed_slots()

        # Track which rooms are used at each time slot
        used = defaultdict(set)
        
        # Sort rooms by capacity (ascending for finding fits, descending for fallback)
        rooms_asc = self.classrooms.sort_values("capacity").reset_index(drop=True)
        rooms_desc = rooms_asc.iloc[::-1].reset_index(drop=True)

        rows = []
        for crn, (day, block) in self.assignment.items():
            if crn in self.unassigned:
                continue  # skip unplaced exams

            size = int(self.G.nodes[crn].get("size", 0) or 0)

            # Try to find a room with sufficient capacity that's not already used
            fit = rooms_asc[
                (rooms_asc["capacity"] >= size)
                & (~rooms_asc["room_name"].isin(used[(day, block)]))
            ].head(1)

            valid = True
            if fit.empty:
                # No perfect fit available, use largest available room
                free = rooms_desc[
                    ~rooms_desc["room_name"].isin(used[(day, block)])
                ].head(1)
                if free.empty:
                    # All rooms used, reuse largest room (will be marked invalid)
                    free = rooms_desc.head(1)
                fit = free
                # Mark as invalid if room capacity is too small
                valid = int(fit.iloc[0]["capacity"]) >= size

            room = fit.iloc[0]
            used[(day, block)].add(room["room_name"])

            # Extract course reference (handle various data types)
            node_data = self.G.nodes[crn]
            course_ref = node_data.get("course_ref", "")
            if isinstance(course_ref, pd.Series):
                course_str = str(course_ref.iloc[0]) if len(course_ref) > 0 else ""
            else:
                course_str = str(course_ref) if course_ref is not None else ""

            # Build result row
            rows.append(
                {
                    "CRN": crn,
                    "Course": course_str,
                    "Day": self.day_names[day],
                    "Block": f"{block} ({self.block_times[block]})",
                    "Room": room["room_name"],
                    "Capacity": int(room["capacity"]),
                    "Size": size,
                    "Valid": valid,  # True if room capacity >= enrollment
                    "Instructor": self.instructors_by_crn.get(crn, set()),
                }
            )

        df = pd.DataFrame(rows)
        # Generate conflict and violation reports
        self._compute_reports(df)
        return df

    # ---------- reporting and statistics ----------
    def _compute_reports(self, df_schedule: pd.DataFrame):
        """
        Compute soft constraint violation reports after scheduling.
        
        Generates reports for:
        - Student back-to-back exams (soft violation)
        - Instructor back-to-back exams (soft violation)
        - Large courses scheduled late in week (soft violation)
        
        Args:
            df_schedule: DataFrame with scheduled exams
            
        Returns:
            None (updates self.student_soft_violations, self.instructor_soft_violations, 
                  self.large_courses_not_early)
        """
        # Map CRNs to their scheduled day and block
        crn_to_dayblock = {
            crn: (self.day_names[d], b)
            for crn, (d, b) in self.assignment.items()
            if crn not in self.unassigned
        }

        # Find students with back-to-back exams
        stu_rows = []
        for sid, grp in self.enrollment.groupby("student_id"):
            per_day = defaultdict(list)
            for crn in grp["CRN"]:
                if crn in crn_to_dayblock:
                    day, b = crn_to_dayblock[crn]
                    per_day[day].append(b)
            for day, blocks in per_day.items():
                blocks.sort()
                # Check for consecutive blocks
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

        # Find instructors with back-to-back exams
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
                # Check for consecutive blocks
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

        # Find large courses scheduled late in week (Thu-Sun = days 3-6)
        late_rows = []
        for crn, (d, b) in self.assignment.items():
            if crn in self.unassigned:
                continue
            size = int(self.G.nodes[crn].get("size", 0) or 0)
            # Large courses (>=100 students) should be scheduled Mon-Wed (days 0-2)
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
        """
        Generate summary statistics for the schedule.
        
        Returns a dictionary with:
        - Hard conflict counts (double-booking, max per day violations)
        - Soft violation counts (back-to-back, large course placement)
        - Schedule statistics (num classes, students, rooms, slots used)
        
        Returns:
            Dictionary with schedule statistics
        """
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

        # Count unique students/instructors with soft violations
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
        """
        Generate report of courses that could not be scheduled.
        
        Returns courses that were marked as unassigned (logically impossible
        to place without breaking hard rules).
        
        Returns:
            DataFrame with columns: CRN, Course, Size, reasons
        """
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

    # ---------- helper methods ----------
    def _check_allowed_slots(self):
        """
        Validate that all assignments are within the allowed day range.
        
        If any assignments are outside max_days, moves them to the first
        allowed slot to keep the schedule valid.
        
        Returns:
            None (modifies self.assignment in place)
        """
        illegal = [
            (crn, d, b) for crn, (d, b) in self.assignment.items() if d >= self.max_days
        ]
        if illegal:
            # Move illegal assignments to first allowed slot
            for crn, _, _ in illegal:
                self.assignment[crn] = self.usable_blocks[0]

