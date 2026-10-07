"""Algorithm 2: saturation-ordered construction plus simulated annealing.

``Scheduler`` (Algorithm 1) colours the conflict graph with DSATUR but then only
uses the colours to *order* exams for a single greedy pass with a lexicographic
penalty. This engine keeps all of ``Scheduler``'s group machinery (combined and
common groups, blockouts, capacity-safe room seating) and replaces the
slot-choice phase with:

1. a weighted objective evaluated incrementally per move,
2. MRV construction ("DSATUR on the slot domain": the time group with the
   fewest remaining violation-free slots is placed first), and
3. conflict-directed simulated annealing under a wall-clock budget.

Hard violations carry a weight (``HARD``) large enough that no soft gain can buy
one; soft terms trade against each other by the configured weights.
"""

import math
import random
import time
from collections import defaultdict

from src.domain.constants import (
    BLOCKS_PER_DAY,
    EARLY_WEEK_CUTOFF,
    LARGE_COURSE_THRESHOLD,
)
from src.domain.models import SchedulingDataset
from src.domain.services.conflict_detector import Conflict
from src.domain.services.scheduler import Scheduler, ScheduleResult


HARD = 10_000
_T_START = 30.0
_T_END = 0.3
_P_SWAP = 0.05
_P_DIRECTED = 0.50
_RESCAN_EVERY = 1500
_CLOCK_EVERY = 256


class AnnealingScheduler(Scheduler):
    """Weighted-objective scheduler: MRV construction + directed annealing.

    Same constructor as ``Scheduler`` plus ``weight_slot_balance`` (cost of
    ``n`` exams sharing a block is ``weight · n²``, so load spreads across all
    blocks instead of the back-to-back-free alternating ones), ``time_budget_seconds``
    (annealing wall-clock budget; 0 returns the construction) and ``seed``.
    ``prioritize_large_courses`` is accepted by ``schedule`` for signature
    compatibility and ignored: the MRV ordering supersedes it.

    Placement unit is the time group. A student sitting several room units of
    one common group counts once in the objective (the double-booking is
    unavoidable wherever the group goes) but is still reported in ``conflicts``.
    """

    def __init__(
        self,
        dataset: SchedulingDataset,
        max_days: int = 7,
        blocks_per_day: int = BLOCKS_PER_DAY,
        student_max_per_day: int = 2,
        instructor_max_per_day: int = 2,
        weight_large_late: int = 1,
        weight_b2b_student: int = 6,
        weight_b2b_instructor: int = 2,
        weight_slot_balance: int = 1,
        merges: dict[str, list[str]] | None = None,
        common_groups: dict[str, list[str]] | None = None,
        time_budget_seconds: float = 15.0,
        seed: int = 0,
        promote_rooms: bool = False,
    ):
        super().__init__(
            dataset,
            max_days=max_days,
            blocks_per_day=blocks_per_day,
            student_max_per_day=student_max_per_day,
            instructor_max_per_day=instructor_max_per_day,
            weight_large_late=weight_large_late,
            weight_b2b_student=weight_b2b_student,
            weight_b2b_instructor=weight_b2b_instructor,
            merges=merges,
            common_groups=common_groups,
            promote_rooms=promote_rooms,
        )
        if time_budget_seconds < 0:
            raise ValueError("time_budget_seconds must be >= 0")
        self.blocks_per_day = blocks_per_day
        self.student_max_per_day = student_max_per_day
        self.instructor_max_per_day = instructor_max_per_day
        self.weight_large_late = weight_large_late
        self.weight_b2b_student = weight_b2b_student
        self.weight_b2b_instructor = weight_b2b_instructor
        self.weight_slot_balance = weight_slot_balance
        self.time_budget_seconds = time_budget_seconds
        self.seed = seed
        self.cost = 0

    # ------------------------------------------------------------------
    # Workflow
    # ------------------------------------------------------------------

    def schedule(self, prioritize_large_courses: bool = False) -> ScheduleResult:
        if not self.dataset.courses:
            return ScheduleResult(
                assignments={},
                room_assignments={},
                conflicts=[],
                colors={},
                unscheduled_groups=list(self.unscheduled_groups.values()),
                unscheduled_crns=set(self.unscheduled_crns),
            )

        self._build_conflict_graph()
        self._init_model()
        self._construct()
        self._improve()
        self._finalize()
        room_assignments = self._assign_rooms()

        return ScheduleResult(
            assignments=dict(self.assignments),
            room_assignments=room_assignments,
            conflicts=list(self.conflicts),
            colors=dict(self.colors),
            unscheduled_groups=list(self.unscheduled_groups.values()),
            unscheduled_crns=set(self.unscheduled_crns),
        )

    # ------------------------------------------------------------------
    # Model: per-time-group data and incremental counts
    # ------------------------------------------------------------------

    def _init_model(self) -> None:
        assert self.graph is not None
        ds = self.dataset
        self.nslots = len(self.available_slots)
        bpd = self.blocks_per_day

        self._tgs: list[str] = [
            tg for tg in self.time_groups if tg not in self.unscheduled_groups
        ]
        n = len(self._tgs)
        self._tg_index = {tg: i for i, tg in enumerate(self._tgs)}
        self._tg_students: list[list[str]] = []
        self._tg_instructors: list[list[str]] = []
        self._tg_late: list[list[int]] = []
        self._tg_units: list[list[str]] = []
        self._tg_sizes: list[list[int]] = []  # room-unit sizes, largest first
        self._tg_enroll: list[int] = []
        self._tg_wdeg: list[int] = []
        for tg in self._tgs:
            crns = self.time_group_crns[tg]
            students: set[str] = set()
            instructors: set[str] = set()
            late = [0] * self.max_days
            wdeg = 0
            for crn in crns:
                students.update(ds.students_by_crn.get(crn, frozenset()))
                instructors.update(ds.instructors_by_crn.get(crn, frozenset()))
                if ds.get_enrollment_count(crn) >= LARGE_COURSE_THRESHOLD:
                    for day in range(self.max_days):
                        late[day] += (
                            max(0, day - EARLY_WEEK_CUTOFF + 1) * self.weight_large_late
                        )
                wdeg += self.graph.degree(crn, weight="weight")
            self._tg_students.append(sorted(students))
            self._tg_instructors.append(sorted(instructors))
            self._tg_late.append(late)
            units = self.time_groups[tg]
            self._tg_units.append(units)
            self._tg_sizes.append(
                sorted((self.unit_enrollment[u] for u in units), reverse=True)
            )
            self._tg_enroll.append(sum(self.unit_enrollment[u] for u in units))
            self._tg_wdeg.append(wdeg)

        # Rooms usable at each slot (blockouts applied), split by the large-only rule
        self._slot_rooms = [self.slot_rooms[slot] for slot in self.available_slots]

        # Neighbours: time groups sharing a student or an instructor
        self._nbrs: list[set[int]] = [set() for _ in range(n)]
        by_entity: dict[str, list[int]] = defaultdict(list)
        for i in range(n):
            for s in self._tg_students[i]:
                by_entity["s:" + s].append(i)
            for t in self._tg_instructors[i]:
                by_entity["i:" + t].append(i)
        for members in by_entity.values():
            for a in members:
                for b in members:
                    if a != b:
                        self._nbrs[a].add(b)

        # Mutable state
        self._slot_of = [-1] * n
        self._st_cnt: dict[str, list[int]] = defaultdict(lambda: [0] * self.nslots)
        self._in_cnt: dict[str, list[int]] = defaultdict(lambda: [0] * self.nslots)
        self._slot_units = [0] * self.nslots
        # Room-unit sizes placed at each slot (unordered)
        self._slot_sizes: list[list[int]] = [[] for _ in range(self.nslots)]
        # Largest single room unit each slot can still seat, per room pool (see
        # ``RoomPools.largest_addable``); None = recompute.
        self._max_single: list[tuple[float, float] | None] = [None] * self.nslots
        # Per student/instructor bitmask (bit = slot index) of slots where one
        # more exam adds a hard violation: slots already holding one of their
        # exams, and every slot of a day already at their daily limit.
        self._st_busy: dict[str, int] = defaultdict(int)
        self._in_busy: dict[str, int] = defaultdict(int)
        self._all_slots = (1 << self.nslots) - 1
        self._day_bits = [
            ((1 << bpd) - 1) << (day * bpd) for day in range(self.max_days)
        ]
        self._active: list[int] = []  # placed groups (SA move candidates)
        self._order: list[int] = []  # MRV placement order
        self.cost = 0
        self._bpd = bpd

    # -- cost pieces ---------------------------------------------------------

    def _day_cost(self, cnt: list[int], day: int, mx: int, w_b2b: int) -> int:
        base = day * self._bpd
        total = double = b2b = prev = 0
        for b in range(self._bpd):
            c = cnt[base + b]
            total += c
            if c > 1:
                double += c - 1
            if c and prev:
                b2b += 1
            prev = c
        over = total - mx if total > mx else 0
        return HARD * (double + over) + w_b2b * b2b

    def _entity_delta(
        self, cnt: list[int], mx: int, w_b2b: int, old: int, new: int
    ) -> int:
        """Cost change for one entity moving one exam old → new (−1 = none)."""
        bpd = self._bpd
        old_day = old // bpd if old >= 0 else -1
        new_day = new // bpd if new >= 0 else -1
        before = 0
        if old_day >= 0:
            before += self._day_cost(cnt, old_day, mx, w_b2b)
        if new_day >= 0 and new_day != old_day:
            before += self._day_cost(cnt, new_day, mx, w_b2b)
        if old >= 0:
            cnt[old] -= 1
        if new >= 0:
            cnt[new] += 1
        after = 0
        if old_day >= 0:
            after += self._day_cost(cnt, old_day, mx, w_b2b)
        if new_day >= 0 and new_day != old_day:
            after += self._day_cost(cnt, new_day, mx, w_b2b)
        if old >= 0:
            cnt[old] += 1
        if new >= 0:
            cnt[new] -= 1
        return after - before

    def _delta(self, i: int, new: int) -> int:
        """Objective change if group i moves to slot ``new`` (−1 = unplace).

        Room feasibility is not included; check ``_fits`` before moving.
        """
        old = self._slot_of[i]
        if old == new:
            return 0
        d = 0
        s_max, s_w = self.student_max_per_day, self.weight_b2b_student
        i_max, i_w = self.instructor_max_per_day, self.weight_b2b_instructor
        st_cnt, in_cnt = self._st_cnt, self._in_cnt
        for s in self._tg_students[i]:
            d += self._entity_delta(st_cnt[s], s_max, s_w, old, new)
        for t in self._tg_instructors[i]:
            d += self._entity_delta(in_cnt[t], i_max, i_w, old, new)
        k = len(self._tg_units[i])
        late = self._tg_late[i]
        w_bal = self.weight_slot_balance
        if old >= 0:
            d -= late[old // self._bpd]
            n_old = self._slot_units[old]
            d += w_bal * ((n_old - k) ** 2 - n_old**2)
        if new >= 0:
            d += late[new // self._bpd]
            n_new = self._slot_units[new]
            d += w_bal * ((n_new + k) ** 2 - n_new**2)
        return d

    def _fits(self, i: int, slot: int) -> bool:
        """True if group i's room units can join those already at ``slot``."""
        sizes = self._tg_sizes[i]
        pools = self._slot_rooms[slot]
        if len(sizes) == 1:
            return pools.single_fits(sizes[0], self._max_single_at(slot))
        merged = sorted(self._slot_sizes[slot] + sizes, reverse=True)
        return pools.fits(merged)

    def _max_single_at(self, slot: int) -> tuple[float, float]:
        """Largest single room unit ``slot`` can still seat, per room pool."""
        cached = self._max_single[slot]
        if cached is not None:
            return cached
        best = self._slot_rooms[slot].largest_addable(
            sorted(self._slot_sizes[slot], reverse=True)
        )
        self._max_single[slot] = best
        return best

    def _refresh_busy(
        self, busy: dict[str, int], key: str, cnt: list[int], mx: int, days: set[int]
    ) -> None:
        """Recompute an entity's busy bits for ``days`` from its slot counts."""
        bpd = self._bpd
        mask = busy[key]
        for day in days:
            base = day * bpd
            counts = cnt[base : base + bpd]
            if sum(counts) >= mx:
                bits = self._day_bits[day]
            else:
                bits = 0
                for block, count in enumerate(counts):
                    if count:
                        bits |= 1 << (base + block)
            mask = (mask & ~self._day_bits[day]) | bits
        busy[key] = mask

    def _move(self, i: int, new: int) -> None:
        """Apply a move (cost delta computed here). Callers check ``_fits``."""
        old = self._slot_of[i]
        if old == new:
            return
        self.cost += self._delta(i, new)
        days = {slot // self._bpd for slot in (old, new) if slot >= 0}
        s_max, i_max = self.student_max_per_day, self.instructor_max_per_day
        for s in self._tg_students[i]:
            cnt = self._st_cnt[s]
            if old >= 0:
                cnt[old] -= 1
            if new >= 0:
                cnt[new] += 1
            self._refresh_busy(self._st_busy, s, cnt, s_max, days)
        for t in self._tg_instructors[i]:
            cnt = self._in_cnt[t]
            if old >= 0:
                cnt[old] -= 1
            if new >= 0:
                cnt[new] += 1
            self._refresh_busy(self._in_busy, t, cnt, i_max, days)
        k = len(self._tg_units[i])
        if old >= 0:
            self._slot_units[old] -= k
            for size in self._tg_sizes[i]:
                self._slot_sizes[old].remove(size)
            self._max_single[old] = None
        if new >= 0:
            self._slot_units[new] += k
            self._slot_sizes[new].extend(self._tg_sizes[i])
            self._max_single[new] = None
        self._slot_of[i] = new

    def recompute_cost(self) -> int:
        """Full objective from scratch (test oracle for the incremental cost)."""
        total = 0
        for cnt in self._st_cnt.values():
            for day in range(self.max_days):
                total += self._day_cost(
                    cnt, day, self.student_max_per_day, self.weight_b2b_student
                )
        for cnt in self._in_cnt.values():
            for day in range(self.max_days):
                total += self._day_cost(
                    cnt, day, self.instructor_max_per_day, self.weight_b2b_instructor
                )
        for i, slot in enumerate(self._slot_of):
            if slot >= 0:
                total += self._tg_late[i][slot // self._bpd]
        w_bal = self.weight_slot_balance
        for slot in range(self.nslots):
            n = self._slot_units[slot]
            total += w_bal * n * n
        return total

    # ------------------------------------------------------------------
    # Construction: MRV
    # ------------------------------------------------------------------

    def _best_slot(self, i: int) -> int | None:
        """Lowest-cost slot where group i fits, or None if it fits nowhere."""
        best: tuple[int, int] | None = None
        for slot in range(self.nslots):
            if not self._fits(i, slot):
                continue
            key = (self._delta(i, slot), slot)
            if best is None or key < best:
                best = key
        return None if best is None else best[1]

    def _count_free(self, i: int) -> int:
        """Slots where unplaced group i fits and adds no hard violation."""
        blocked = 0
        for s in self._tg_students[i]:
            blocked |= self._st_busy.get(s, 0)
        for t in self._tg_instructors[i]:
            blocked |= self._in_busy.get(t, 0)
        free = self._all_slots & ~blocked
        count = 0
        while free:
            low = free & -free
            free ^= low
            if self._fits(i, low.bit_length() - 1):
                count += 1
        return count

    def _construct(self) -> None:
        n = len(self._tgs)
        unplaced = set(range(n))
        free = [self._count_free(i) for i in range(n)]
        while unplaced:
            i = min(
                unplaced,
                key=lambda j: (free[j], -self._tg_wdeg[j], -self._tg_enroll[j], j),
            )
            unplaced.remove(i)
            slot = self._best_slot(i)
            if slot is None:
                self._mark_unscheduled(
                    self._tgs[i], self._no_slot_reason(self._tg_units[i])
                )
                continue
            self._move(i, slot)
            self._active.append(i)
            self._order.append(i)
            for j in self._nbrs[i]:
                if j in unplaced:
                    free[j] = self._count_free(j)

    # ------------------------------------------------------------------
    # Improvement: conflict-directed simulated annealing
    # ------------------------------------------------------------------

    def _improve(self) -> None:
        budget = self.time_budget_seconds
        active = self._active
        if budget <= 0 or len(active) < 2 or self.nslots < 2 or self.cost == 0:
            return
        rng = random.Random(self.seed)  # noqa: S311
        best_cost = self.cost
        best_state = list(self._slot_of)
        start = time.monotonic()
        deadline = start + budget
        temperature = _T_START
        violating: list[int] = []
        it = 0
        while self.cost > 0:
            it += 1
            if it % _RESCAN_EVERY == 1:
                violating = [i for i in active if self._delta(i, -1) <= -HARD]
            if it % _CLOCK_EVERY == 0:
                now = time.monotonic()
                if now >= deadline:
                    break
                frac = (now - start) / budget
                temperature = _T_START * (_T_END / _T_START) ** frac

            r = rng.random()
            if r < _P_SWAP:
                self._try_swap(rng, temperature)
            else:
                if violating and r < _P_SWAP + _P_DIRECTED:
                    i = rng.choice(violating)
                    slot = self._best_slot(i)
                    if slot is None:
                        continue
                else:
                    i = active[rng.randrange(len(active))]
                    slot = rng.randrange(self.nslots)
                    if not self._fits(i, slot):
                        continue
                d = self._delta(i, slot)
                if d <= 0 or rng.random() < math.exp(-d / temperature):
                    self._move(i, slot)

            if self.cost < best_cost:
                best_cost = self.cost
                best_state = list(self._slot_of)

        self._restore(best_state)

    def _try_swap(self, rng: random.Random, temperature: float) -> None:
        """Exchange the full contents of two slots; revert unless accepted."""
        sa, sb = rng.sample(range(self.nslots), 2)
        ia = [i for i in self._active if self._slot_of[i] == sa]
        ib = [i for i in self._active if self._slot_of[i] == sb]
        if not ia and not ib:
            return
        before = self.cost
        for i in ia + ib:
            self._move(i, -1)
        feasible = True
        for group, target in ((ib, sa), (ia, sb)):
            for i in group:
                if not self._fits(i, target):
                    feasible = False
                    break
                self._move(i, target)
            if not feasible:
                break
        d = self.cost - before
        if feasible and (d <= 0 or rng.random() < math.exp(-d / temperature)):
            return
        for i in ia + ib:
            self._move(i, -1)
        for group, target in ((ia, sa), (ib, sb)):
            for i in group:
                self._move(i, target)

    def _restore(self, slots: list[int]) -> None:
        for i in self._active:
            self._move(i, -1)
        for i in self._active:
            self._move(i, slots[i])

    # ------------------------------------------------------------------
    # Finalize: assignments and conflicts from the final state
    # ------------------------------------------------------------------

    def _finalize(self) -> None:
        for rank, i in enumerate(self._order):
            for crn in self.time_group_crns[self._tgs[i]]:
                self.colors[crn] = rank
        for i in self._active:
            slot = self._slot_of[i]
            day, block = self.available_slots[slot]
            for crn in self.time_group_crns[self._tgs[i]]:
                self.assignments[crn] = (day, block)
            self.slot_units[(day, block)].extend(self._tg_units[i])
        self.conflicts = self._recompute_conflicts()

    def _recompute_conflicts(self) -> list[Conflict]:
        """Hard conflicts of the final assignment.

        A student sits once per room unit (two units of one common group are a
        real double-booking); an instructor sits once per time group (sections of
        one common exam run concurrently by design), matching what Algorithm 1
        reports.
        """
        ds = self.dataset
        # entity → day → block → [first CRN of each sitting, in CRN order]
        sittings: dict[tuple[str, str], dict[int, dict[int, list[str]]]] = defaultdict(
            lambda: defaultdict(lambda: defaultdict(list))
        )
        seen: set[tuple[str, str, str]] = set()
        for crn in sorted(self.assignments):
            day, block = self.assignments[crn]
            unit = self.crn_to_room_unit[crn]
            tg = self.crn_to_time_group[crn]
            entities = [("student", s, unit) for s in ds.students_by_crn.get(crn, ())]
            entities += [
                ("instructor", t, tg) for t in ds.instructors_by_crn.get(crn, ())
            ]
            for kind, entity, scope in entities:
                if (kind, entity, scope) in seen:
                    continue
                seen.add((kind, entity, scope))
                sittings[(kind, entity)][day][block].append(crn)

        limits = {
            "student": self.student_max_per_day,
            "instructor": self.instructor_max_per_day,
        }
        conflicts: list[Conflict] = []
        for (kind, entity), days in sittings.items():
            for day, blocks in days.items():
                count = 0
                for block in sorted(blocks):
                    crns = blocks[block]
                    for extra in crns[1:]:
                        conflicts.append(
                            Conflict(
                                conflict_type=f"{kind}_double_book",
                                entity_id=entity,
                                crn=extra,
                                conflicting_crn=crns[0],
                                day=day,
                                block=block,
                            )
                        )
                    for crn in crns:
                        count += 1
                        if count > limits[kind]:
                            conflicts.append(
                                Conflict(
                                    conflict_type=f"{kind}_gt_max_per_day",
                                    entity_id=entity,
                                    crn=crn,
                                    conflicting_crn=None,
                                    day=day,
                                    block=block,
                                )
                            )
        return conflicts
