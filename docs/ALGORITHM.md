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
