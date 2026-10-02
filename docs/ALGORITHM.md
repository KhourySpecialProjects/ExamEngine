# Algorithm Guide

DSATUR graph coloring algorithm for exam scheduling.

## Problem Overview

Exam scheduling is a constraint satisfaction problem:

- **Nodes:** Course sections (exams)
- **Edges:** Conflicts (shared students between courses)
- **Colors:** Time slots
- **Goal:** Minimize colors (time slots) while respecting constraints

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

### Hard Constraints (Must satisfy)

| Constraint           | Description                                                     |
| -------------------- | --------------------------------------------------------------- |
| No student conflicts | Student can't have 2 exams at same time                         |
| Room capacity        | Room must fit course enrollment                                 |
| Time slot limits     | Use only available time slots (`max_days` × `blocks_per_day`)   |

### Time Slots

Each day has up to 5 exam blocks: 9AM-11AM, 11:30AM-1:30PM, 2PM-4PM, 4:30PM-6:30PM, 7PM-9PM. The Generate Schedule dialog chooses 4 or 5 blocks per day (`blocks_per_day`, default 5); with 4 the 7PM-9PM block is never used. `max_days` (1–7, Monday first) sets the number of days.

### Soft Constraints (Optimize for)

| Constraint           | Description                           | Weight |
| -------------------- | ------------------------------------- | ------ |
| No back-to-back      | Avoid consecutive exams for students  | High   |
| Max 2 per day        | Limit student exams per day           | High   |
| Large class priority | Schedule large classes in prime slots | Medium |
| Room efficiency      | Minimize wasted capacity              | Low    |

### Constraint Relaxation

When the available time slots are insufficient:

1. Allow controlled back-to-back exams
2. Extend exam period (add slots)
3. Split large courses across multiple rooms

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
moves to a block where all of that block's room units still fit (`seats_fit`).

The quadratic `weight_slot_balance` term (default 1) is what keeps every block in use:
without it the back-to-back term alone makes an alternating 9AM / 2PM / 7PM pattern
optimal whenever rooms allow, leaving the 11:30AM and 4:30PM blocks empty. The marginal
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

`prioritize_large_courses` is accepted and ignored by Algorithm 2. The dialog's **Avoid
Back-to-Back Exams** switch affects only Algorithm 2: off sets both back-to-back weights
to 0 (Algorithm 1 has never read it).

### Measured on `sample_data_large` (generated by `backend/script/gen_test_data.py`)

hard = double-bookings + over-2-per-day; b2b = student-days with adjacent exams;
unscheduled = sections larger than every room. Optimized uses a 15 s budget.

| days × blocks | Classic | Optimized |
| --- | --- | --- |
| 7 × 5 | hard 1, b2b 53 | hard 0, b2b 0–6 |
| 7 × 4 | hard 2, b2b 184 | hard 0, b2b 127 |
| 5 × 5 | hard 60, b2b 438 | hard 10, b2b 406 |
| 5 × 4 | hard 56, b2b 890 | hard 6, b2b 878 |

Both leave the same 6 sections unscheduled (larger than every room). The Optimized
back-to-back count varies a little between runs because annealing is time-bounded.

## Constraint Relaxation

When the available time slots are insufficient:

1. Allow controlled back-to-back exams
2. Extend exam period (add slots)
3. Split large courses across multiple rooms

## References

- [DSATUR Algorithm (Wikipedia)](https://en.wikipedia.org/wiki/DSatur)
- [Graph Coloring Problem](https://en.wikipedia.org/wiki/Graph_coloring)
