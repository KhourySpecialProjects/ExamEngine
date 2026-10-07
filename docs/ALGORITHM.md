# Algorithm Guide

Two scheduling engines, both built on a graph-coloring model: **Classic** (DSATUR greedy) and
**Optimized** (saturation construction + simulated annealing, see Algorithm 2 below).

## Problem Overview

Exam scheduling is modelled as graph coloring:

- **Nodes:** Course sections (exams)
- **Edges:** Conflicts (shared students between courses)
- **Time slots:** fixed by the run settings: `max_days × blocks_per_day`. The engines never add
  slots.
- **Goal:** place every exam in one of those slots, with as few hard conflicts as possible, then
  as few soft-constraint penalties as possible. Classic uses the DSATUR colours only to decide the
  order in which exams are placed (see "Why a second algorithm").

## DSATUR Algorithm

DSATUR (Degree of Saturation) is a greedy graph coloring algorithm that prioritizes vertices with the highest "saturation degree" — the number of different colors already used by neighboring vertices.

### Why DSATUR?

| Algorithm              | Time Complexity   | Quality | Use Case       |
| ---------------------- | ----------------- | ------- | -------------- |
| Greedy (largest first) | O(V + E)          | Good    | Quick baseline |
| **DSATUR**             | O(V² log V)       | Better  | Production     |
| Tabu Search            | O(iterations × V) | Best    | Optimization   |

DSATUR balances speed and solution quality, making it ideal for real-time scheduling.

### Algorithm Steps

```
1. Initialize all vertices as uncolored
2. While uncolored vertices exist:
   a. Select vertex with highest saturation degree
      (ties broken by highest degree)
   b. Assign lowest available color that satisfies constraints
   c. Update saturation degrees of neighbors
3. Return coloring
```

## Constraints

### Always enforced

| Constraint        | Description                                                                                   |
| ----------------- | --------------------------------------------------------------------------------------------- |
| Room capacity     | An exam is only placed in a block where it (and every exam already there) gets its own unblocked room at least its size (`seats_fit`). Rooms are never over capacity; an exam that can't be seated is unscheduled with a reason. |
| Large-only room   | Optional (rooms.csv `LargeOnly`). The marked room seats more than every other room and takes **exactly** the room units larger than the largest other room (the cutoff); those units can use no other room. Without a marked room every room is open to every exam that fits. See `domain/services/room_fit.py`. |
| Time slots        | Only the available slots (`max_days` × `blocks_per_day`) are used                            |
| Combined / common | A group always shares one block and is never split (see below)                               |

### Hard conflicts (minimised first, reported)

Both engines minimise these before anything else, but can't always avoid them; every one left is
stored in the schedule's conflict analysis and shown on the Conflicts tab.

| Conflict                      | Description                                                                  |
| ----------------------------- | ---------------------------------------------------------------------------- |
| Student double-booked         | A student has two exams in the same block                                    |
| Instructor double-booked      | An instructor has two exams in the same block                                |
| Student over the daily limit  | A student has more than `student_max_per_day` exams on one day (dialog 1–5)  |
| Instructor over the daily limit | An instructor has more than `instructor_max_per_day` exams on one day (dialog 1–5) |

### Time Slots

Each day has up to 5 exam blocks: 8AM-10AM, 10:30AM-12:30PM, 1PM-3PM, 3:30PM-5:30PM, 6PM-8PM (`EXAM_BLOCKS` in `backend/src/domain/constants.py`, the only definition). The engines work with block indices (0 = 8AM-10AM); the clock times are only stored and shown. The Generate Schedule dialog chooses 4 or 5 blocks per day (`blocks_per_day`, default 5); with 4 the 6PM-8PM block is never used. `max_days` (1–7, Monday first) sets the number of days.

Before the times were corrected, the blocks were labeled 9AM-11AM, 11:30AM-1:30PM, 2PM-4PM, 4:30PM-6:30PM and 7PM-9PM (`LEGACY_EXAM_BLOCKS`). At startup the backend relabels any saved data still on those times to the block with the same index (`backend/src/core/relabel_blocks.py`): time slots, stored conflict analyses, late additions and room blockout counts. Room blockout files may still name the old times; they parse to the same block index.

### Soft constraints (optimised after hard conflicts)

| Constraint              | Description                                                              | Classic | Optimized |
| ----------------------- | ------------------------------------------------------------------------ | ------- | --------- |
| Large course late       | A course of 100+ students (`LARGE_COURSE_THRESHOLD`) after Wednesday: 1 point per day late | 1st | weight 1 |
| Student back-to-back    | A student with exams in adjacent blocks on the same day                  | 2nd     | weight 6 (0 when Avoid Back-to-Back is off) |
| Instructor back-to-back | An instructor with exams in adjacent blocks on the same day              | 3rd     | weight 2 (0 when Avoid Back-to-Back is off) |
| Instructor daily load   | Exams the instructor already has that day                                | 4th     | –         |
| Slot load               | Students and exams already in the block (Classic); Σ (exams in block)² (Optimized) | 5th–6th | weight 1 |

Classic compares candidate blocks lexicographically: fewest hard conflicts, then the soft
terms in the order above (`SoftPenalty.as_tuple`), then the earliest block. Optimized sums one
weighted objective (see Algorithm 2). Room usage beyond the capacity rule is not scored.

### What the analysis reports

After either engine runs, `ScheduleAnalyzer` (`backend/src/domain/services/schedule_analyzer.py`)
builds the stored conflict analysis from the final assignment and the dataset, the same way for
both engines: the hard conflicts above, student and instructor back-to-backs (one entry per
person per day), and large courses late (`large_courses_not_early`: 100+ students on Thursday
or later).

## Combined and Common Exams

Two optional inputs group CRNs together (see `Scheduler(merges=..., common_groups=...)`):

| Kind                  | Input file                         | Same time block | Room                                  |
| --------------------- | ---------------------------------- | --------------- | ------------------------------------- |
| **Combined**          | `combined_exams` (`ExamGroup,CRN`) | Yes             | One shared room                       |
| **Common**            | `common_exams` (`Common_Group,CRN`) | Yes             | A distinct room per member (anti-leak) |
| **Common + combined** | both                               | Yes             | One room per combined group, one per other CRN |

A common group may contain combined groups. If any CRN of a combined group is listed in a common group, the whole combined group belongs to it. Example: combined `{11111, 22222}` and common `BIOL101 = {11111, 33333, 44444}` → one block, three rooms: `11111+22222`, `33333`, `44444`.

Terms used by the scheduler:

- **Room unit** — a combined group or a lone CRN; gets exactly one room.
- **Time group** — a common group (its room units) or a lone room unit; all its CRNs share one block.

A CRN in two combined groups, a CRN in two common groups, or a combined group split across common groups raises `ValueError`.

### Pipeline changes

1. **Upfront feasibility.** A combined group larger than the largest room is unscheduled. A common group is unscheduled **as a whole** if it contains such a combined group, or if its room units cannot all be seated at once in distinct rooms (greedy: units by enrollment descending, each into the smallest unused room that fits; blockouts ignored at this stage).
2. **Contraction.** Before DSATUR, every multi-CRN time group is collapsed into one virtual node carrying the union of its members' external edges (max weight); edges inside the group are dropped. All members receive the virtual node's color.
3. **Ordering.** Common groups are placed **first** — most room units, then largest total enrollment — so their room units claim seats before other exams compete for them. Everything else follows the usual color/size ordering, one representative per time group.
4. **Slot choice.** Conflicts and soft penalties are summed over all CRNs of the time group. A block is admissible only if every room unit already placed there, plus the group's own, can each still have a **distinct** room that is unblocked at that block (`room_blockouts`) and at least its size (`seats_fit`: sorted largest first, the k-th largest exam must fit the k-th largest room). This applies to every group — single sections included — so no exam ever takes a room another exam needs. If no block is admissible, the whole group (or section) is unscheduled. Students enrolled in two or more room units of one common group are reported as unavoidable `student_double_book` conflicts.
5. **Room assignment.** `_assign_rooms` seats each block's room units **largest first**, each in the smallest free, unblocked room that fits. Slot choice guarantees this always succeeds, so rooms are never over capacity and no placed exam is left without a room. A section in no group that is larger than every room is unscheduled up front (reason `"{n} students; largest room seats {m}"`, flagged at upload as `courses.oversized_sections`); one with no admissible block is unscheduled with a reason too. Both are reported with kind `section`. Rooms listed twice in `rooms.csv` count once (the last row wins).

**Large-only room.** When rooms.csv marks a room `LargeOnly`, steps 1, 4 and 5 treat it and the other rooms as two separate pools (`RoomPools` in `room_fit.py`): room units above the cutoff (the largest other room's capacity) are matched only against the large-only room, the others only against the other rooms. Each pool keeps the largest-first matching, so every check stays exact. Unscheduled reasons then mention the rule, e.g. `"No time block has the large-only room {name} free and unblocked for its {n} students"`.

The Schedule Validator re-checks these outcomes independently: `rooms.unscheduled_had_no_room` warns when an unscheduled section or combined group (outside common groups) had a free, unblocked room it was allowed to use in some block of the exam window.

Unsatisfiable groups are never split or partially placed. `ScheduleResult.unscheduled_groups` lists each one as `UnscheduledGroup(kind, label, reason, crns)` (`kind` is `combined`, `common` or `section`; a combined group inside an unscheduled common group is reported once, under the common group; a `section` is a single CRN in no group, with `label` the CRN and `crns` just that CRN), and `ScheduleResult.unscheduled_crns` lists every CRN left with neither block nor room. The CRNs are persisted as assignments with no time slot and no room; the groups are saved in the schedule's conflict analysis and returned as `unscheduled_groups` (`[{kind, group, reason, crns}]`) by `POST /api/schedule/generate/{dataset_id}` and `GET /api/schedule/{schedule_id}` (empty for schedules generated before this was recorded). The UI shows them on the Statistics "Unscheduled Exams" card and on the List view's unscheduled rows; groups and sections the upload already knows cannot fit are also listed under the dataset in the sidebar. Exported rows whose room capacity is below their size (possible only in schedules generated before rooms were capped) have `Valid = false`.

## Algorithm 2: Saturation + Annealing

The Generate Schedule dialog offers two algorithms (`algorithm` query parameter on
`POST /api/schedule/generate/{dataset_id}`; stored as `run.algorithm_name`):

| UI name | `algorithm` | `algorithm_name` | Engine |
| --- | --- | --- | --- |
| **Classic** — DSATUR greedy | `dsatur` (default) | `DSATUR` | `Scheduler` (everything above) |
| **Optimized** — Saturation + Annealing | `annealing` | `Annealing` | `AnnealingScheduler` |

`AnnealingScheduler` (`backend/src/domain/services/annealing_scheduler.py`) subclasses
`Scheduler` and keeps its group machinery unchanged — combined/common groups, upfront
feasibility, the per-block seat check, blockouts, `_assign_rooms`, `ScheduleResult`.
Only the slot-choice phase differs.

### Why a second algorithm

Algorithm 1 colours the conflict graph but uses the colours only to *order* exams for a
single greedy pass, and compares slots lexicographically (`SoftPenalty.as_tuple`), so
`large_course_late` always outranks `back_to_back_students` and the configured weights
never trade against each other. On `sample_data_large` it leaves hard conflicts and
student back-to-backs that Algorithm 2 removes (see the table below).

### Objective

One weighted sum, evaluated incrementally per move (only the moved group's students and
instructors on the two affected days):

```
cost = HARD · (student double-bookings + student over-max/day
             + instructor double-bookings + instructor over-max/day)
     + weight_b2b_student    · student adjacent-block pairs
     + weight_b2b_instructor · instructor adjacent-block pairs
     + weight_large_late     · Σ days late (large courses after Wednesday)
     + weight_slot_balance   · Σ_blocks (exams in block)²
```

`HARD = 10_000`, so no soft gain can buy a hard violation, while soft terms trade by
their weights. Room capacity is not a cost term but a hard filter: a group only ever
moves to a block where all of that block's room units still fit (`RoomPools.fits`, i.e.
`seats_fit` per pool).

The quadratic `weight_slot_balance` term (default 1) is what keeps every block in use:
without it the back-to-back term alone makes an alternating 8AM / 1PM / 6PM pattern
optimal whenever rooms allow, leaving the 10:30AM and 3:30PM blocks empty. The marginal
cost of adding an exam to a block holding `n` is `2n + 1`, so empty blocks fill first
and the optimizer trades a few back-to-backs for an even load.

### Phases

1. **MRV construction** (DSATUR's saturation rule applied to the real slot domain):
   repeatedly place the time group with the fewest remaining violation-free blocks
   (ties: weighted degree, then enrollment) in its lowest-cost block. Only neighbours of
   the placed group have their counts refreshed; each student and instructor keeps a
   bitmask of the blocks where one more exam would be a hard violation, so a refresh is
   a few bitwise ORs. A group with no block where its room units fit is left
   unscheduled, as in Algorithm 1.
2. **Conflict-directed simulated annealing** for `time_budget_seconds` (dialog: 5/15/30 s;
   0 skips this phase). Moves: random group → random block; a group currently in a hard
   violation → its best block (half of the moves); swap the contents of two blocks.
   Geometric cooling 30 → 0.3 over wall-clock time; best state kept. Because cooling
   and the deadline follow the clock, the same `seed` reproduces a run exactly only
   with a budget of 0.
3. **Finalize**: `conflicts` are recomputed from the final assignment (a student sits
   once per room unit, an instructor once per time group, as Algorithm 1 reports), then
   rooms are assigned exactly as in Algorithm 1.

Algorithm 2 ignores the `prioritize_large_courses` toggle because it always prioritizes
large courses: the large-course-late penalty (`weight_large_late`) applies to every run, and
the UI shows the setting as "Always on in Optimized". The dialog's **Avoid
Back-to-Back Exams** switch affects only Algorithm 2: off sets both back-to-back weights
to 0 (Algorithm 1 has never read it).

### Measured on `sample_data_large` (generated by `backend/script/gen_test_data.py`)

hard = double-bookings + over-the-daily-limit (runs used a student limit of 2 per day);
b2b = student-days with adjacent exams;
unscheduled = sections larger than every room. Optimized uses a 15 s budget.

| days × blocks | Classic | Optimized |
| --- | --- | --- |
| 7 × 5 | hard 1, b2b 53 | hard 0, b2b 0–6 |
| 7 × 4 | hard 2, b2b 184 | hard 0, b2b 127 |
| 5 × 5 | hard 60, b2b 438 | hard 10, b2b 406 |
| 5 × 4 | hard 56, b2b 890 | hard 6, b2b 878 |

Both leave the same 6 sections unscheduled (larger than every room). The Optimized
back-to-back count varies a little between runs because annealing is time-bounded.

## Late add

Places one exam that missed generation (a CRN in enrollments.csv but not in the schedule) into
a saved schedule without moving any scheduled exam or changing any room
(`backend/src/domain/services/late_add.py`, pure domain code). The inputs are the base
schedule's exams (block, room, course code, instructor), the dataset's combined and common
groups, the unfiltered enrollments, the rooms and room blockouts, the base run's settings
(`max_days`, `blocks_per_day`, the two daily limits) and the late exam (CRN, course code,
instructor ID, its students; size = distinct students).

`search_placements` evaluates every block of the base run's window (`max_days` ×
`blocks_per_day`, at most 7 × 5), so the ranking is exact; `evaluate_placement` evaluates one
block. Neither reuses the scheduler engines (they re-seat every exam of a block) or the
Validator's checks (the Validator stays an independent re-check). Per block:

| Term | Rule |
| --- | --- |
| Free rooms | Not used by a base exam in that block and not blocked out then, and allowed by the large-only rule (a late exam over the cutoff may only use the large-only room; any other may not). Best fit = the smallest such room with capacity ≥ size; the other fitting free rooms are listed too |
| Student double-booked | A late-exam student already sits an exam in that block (with the clashing CRNs) |
| Student over the daily limit | The student's exams that day, the late one included, exceed `student_max_per_day` |
| Instructor double-booked / over the daily limit | The same for the instructor ID |
| Back-to-back (students, instructor) | An exam in the adjacent block of the same day |
| Large course late | 100+ students on Thursday or later (`LARGE_COURSE_THRESHOLD`, `EARLY_WEEK_CUTOFF`, as `ScheduleAnalyzer`) |

**Counting.** Existing exams count as the Validator counts them: per distinct (unit, block) on
the day. A student's unit is the exam unit (a combined group, else the CRN), so the CRNs of one
combined exam count once, roomed or not. The instructor's unit is the time group: a common group
(closed over combined groups, so a combined group listed partly in a common group joins it
whole), else a combined group, else the CRN, so one common exam across several rooms counts
once. Two separate exams in one block count twice, so a person already double-booked in the base
counts two exams in that block. The late exam is always one more exam, also in a block where
the person already sits one (per exam, EXENG-81). Students are counted as distinct people; the
instructor counts 0 or 1 per term. The instructor ID matches a base exam's stored instructor by
trimmed exact string; blank and `nan` never match (EXENG-79).

**Outcomes.**

- **Clear:** at least one block has no student or instructor hard conflict and a fitting free
  room; only those blocks are candidates.
- **Least conflicts:** no clear block; every block with a fitting free room is a candidate.
- **No room:** no block has a fitting free room; nothing can be placed, and each block reports
  its largest free room.

**Ranking** (lexicographic, fewest first): student double-books, students over the daily limit,
instructor double-book, instructor over the daily limit, student back-to-backs, instructor
back-to-back, large course late, then day and block (earliest first).

The search also returns the instructor's existing exams in the base schedule (to confirm the
ID matched) and the base exams with the same course code (sibling sections, information only).

**Saving** (`POST /api/schedule/{id}/late-add`, see `DATA.md`) re-runs `evaluate_placement` for
the chosen block and stores a new schedule. Its conflict analysis is not recomputed:
`late_exam_analysis` (`backend/src/domain/services/late_add_analysis.py`) deep-copies the base's
stored analysis and adds the late exam's delta in `ScheduleAnalyzer`'s shapes: one
double-book entry per (person, base CRN in the block), one daily-limit entry per person over
the limit, back-to-back entries per (person, day) extended with the late block or added, a
large-course-late entry if it applies, and statistics recomputed from the lists and the exams.

## References

- [DSATUR Algorithm (Wikipedia)](https://en.wikipedia.org/wiki/DSatur)
- [Graph Coloring Problem](https://en.wikipedia.org/wiki/Graph_coloring)
