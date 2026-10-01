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

| Constraint           | Description                              |
| -------------------- | ---------------------------------------- |
| No student conflicts | Student can't have 2 exams at same time  |
| Room capacity        | Room must fit course enrollment          |
| Time slot limits     | Use only available time slots (25 total) |

### Soft Constraints (Optimize for)

| Constraint           | Description                           | Weight |
| -------------------- | ------------------------------------- | ------ |
| No back-to-back      | Avoid consecutive exams for students  | High   |
| Max 2 per day        | Limit student exams per day           | High   |
| Large class priority | Schedule large classes in prime slots | Medium |
| Room efficiency      | Minimize wasted capacity              | Low    |

### Constraint Relaxation

When 25 time slots are insufficient:

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
3. **Ordering.** Common groups are placed **first** — most room units, then largest total enrollment — so their rooms are reserved before other exams compete for them. Everything else follows the usual color/size ordering, one representative per time group.
4. **Slot choice.** Conflicts and soft penalties are summed over all CRNs of the time group. For a room-reserving group — a common group, or a combined group — a block is admissible only if its room units pack (same greedy) into rooms that are neither blocked (`room_blockouts`) nor already reserved by an earlier group at that block. If no block is admissible, the whole group is unscheduled; a combined group is never put in a room smaller than its enrollment. Students enrolled in two or more room units of one common group are reported as unavoidable `student_double_book` conflicts.
5. **Room reservation.** On placement the packed rooms are reserved for that block. `_assign_rooms` starts from these reservations, then assigns every remaining single-CRN exam the smallest free, unblocked room that fits (falling back to the largest free room, else leaving it unroomed).

Unsatisfiable groups are never split or partially placed. `ScheduleResult.unscheduled_groups` lists each one as `UnscheduledGroup(kind, label, reason, crns)` (`kind` is `combined` or `common`; a combined group inside an unscheduled common group is reported once, under the common group), and `ScheduleResult.unscheduled_crns` lists every CRN left with neither block nor room. The CRNs are persisted as assignments with no time slot and no room; the groups are saved in the schedule's conflict analysis and returned as `unscheduled_groups` (`[{kind, group, reason, crns}]`) by `POST /api/schedule/generate/{dataset_id}` and `GET /api/schedule/{schedule_id}` (empty for schedules generated before this was recorded). The UI shows them on the Statistics "Unscheduled Exams" card and on the List view's unscheduled rows; groups the upload already knows cannot fit are also listed under the dataset in the sidebar.

## Future Improvements

### Tabu Search Enhancement

For further optimization after DSATUR:

```python
def tabu_search(initial_solution, iterations=1000):
    """
    Local search to improve DSATUR solution.

    Moves: Swap time slots between courses and evaluate cost.
    Tabu: Prevent cycling by tracking recent moves.
    """
    best = current = initial_solution
    tabu_list = []

    for _ in range(iterations):
        neighbors = generate_neighbors(current)
        neighbors = [n for n in neighbors if n not in tabu_list]

        current = best_neighbor(neighbors)
        tabu_list.append(current)

        if evaluate(current) < evaluate(best):
            best = current

    return best
```

### Constraint Relaxation

When 25 time slots are insufficient:

1. Allow controlled back-to-back exams
2. Extend exam period (add slots)
3. Split large courses across multiple rooms

## References

- [DSATUR Algorithm (Wikipedia)](https://en.wikipedia.org/wiki/DSatur)
- [Graph Coloring Problem](https://en.wikipedia.org/wiki/Graph_coloring)
