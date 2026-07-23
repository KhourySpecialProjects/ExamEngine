#!/usr/bin/env python3
"""Generate a coherent, tunable exam-scheduling test dataset.

Emits four CSVs matching the upload schema:
    courses.csv, enrollments.csv, rooms.csv, room_blockouts.csv

Enrollment is modeled as independent "program" cliques rather than uniform
random assignment: each student belongs to one program and draws most of their
courses from it, with a small shared gen-ed pool bridging programs. Disjoint
programs can reuse the same time slots, so the conflict graph has realistic
density (its chromatic number tracks the clique size, not the course count).
Class sizes come out right-skewed, and each course's declared Enrollment equals
its actual number of enrollment rows.

Deterministic for a given --seed. Output is regenerable, so the output dir is
gitignored rather than committed. Example:

    python backend/script/gen_test_data.py \
        --students 5000 --courses 400 --rooms 35 --seed 4535 --out sample_data_large

Notes on exercising unplaced/unroomed paths (not produced by generation alone):
  - Unscheduled exams require an over-capacity *merge* group set via the API
    (POST /datasets/{id}/merges) after upload.
  - Unroomed exams require enough --blockouts that every room is blocked at some
    used slot.
"""

import argparse
import csv
import os
import random
import statistics
from collections import defaultdict


DEPTS = ["CSCI", "MATH", "PHYS", "DS", "BIOL", "CHEM", "ECON", "PSYC", "ENGL", "HIST"]
TERM = "Fall 2025"
LOADS = [2, 3, 4, 5]
DAYS = 5
BLOCKS = 5


def build_rooms(
    n: int, rng: random.Random, max_cap: int = 250
) -> list[tuple[str, int]]:
    """Right-skewed capacities with one guaranteed large hall."""
    tiers = [(30, 60, 0.45), (70, 120, 0.30), (130, 180, 0.17), (200, 250, 0.08)]
    caps = [max_cap]
    for _ in range(max(0, n - 1)):
        r = rng.random()
        acc = 0.0
        pick = rng.randint(30, 60)
        for lo, hi, w in tiers:
            acc += w
            if r <= acc:
                pick = rng.randint(lo, hi)
                break
        caps.append(pick)
    rng.shuffle(caps)
    return [(f"Room {i + 1:03d}", cap) for i, cap in enumerate(caps)]


def build_dataset(args: argparse.Namespace) -> dict[str, list]:
    rng = random.Random(args.seed)  # noqa: S311 - deterministic test data, not crypto

    n_prog = max(1, args.courses // max(1, args.clique_size))
    prog_courses: dict[int, list[str]] = defaultdict(list)
    courses: list[tuple[str, str, str, int]] = []  # crn, code, dept, program
    crn = 20000
    for i in range(args.courses):
        p = i % n_prog
        dept = DEPTS[p % len(DEPTS)]
        code = f"{dept} {1000 + p * 5 + (i // n_prog)}"
        c = str(crn)
        crn += 1
        courses.append((c, code, dept, p))
        prog_courses[p].append(c)
    all_crns = [c[0] for c in courses]

    # Shared gen-ed pool: one course from every few programs.
    step = max(1, n_prog // max(1, args.gen_eds))
    gen_pool = [prog_courses[p][0] for p in range(0, n_prog, step)][: args.gen_eds]
    if not gen_pool:
        gen_pool = all_crns[: args.gen_eds]

    faculty = {
        p: [f"Dr. {chr(65 + (p % 26))}{j}" for j in range(1, 7)] for p in range(n_prog)
    }
    instr_of = {c: rng.choice(faculty[p]) for c, _, _, p in courses}

    # Load distribution weighted toward the requested average.
    weights = [max(0.05, 1 - abs(load - args.avg_load) / 3) for load in LOADS]

    per_crn: dict[str, int] = defaultdict(int)
    enroll: list[tuple[str, str]] = []
    for s in range(1, args.students + 1):
        sid = f"{100000 + s:09d}"
        p = rng.randrange(n_prog)
        load = rng.choices(LOADS, weights)[0]
        picked: set[str] = set()
        guard = 0
        while len(picked) < load and guard < 50:
            guard += 1
            if rng.random() < 0.9 and prog_courses[p]:
                picked.add(rng.choice(prog_courses[p]))
            elif gen_pool:
                picked.add(rng.choice(gen_pool))
        for c in sorted(picked):
            enroll.append((sid, c))
            per_crn[c] += 1

    # Floor tiny courses so none are empty.
    for c in all_crns:
        while per_crn[c] < args.min_size:
            enroll.append((f"{100000 + rng.randint(1, args.students):09d}", c))
            per_crn[c] += 1

    rooms = build_rooms(args.rooms, rng)
    small_rooms = [r for r, cap in rooms if cap < 120] or [r for r, _ in rooms]
    blockouts = [
        [rng.choice(small_rooms), rng.randrange(DAYS), rng.randrange(BLOCKS)]
        for _ in range(args.blockouts)
    ]

    course_rows = [
        [c, code, per_crn[c], instr_of[c], dept, TERM] for c, code, dept, _ in courses
    ]
    return {
        "courses": course_rows,
        "enrollments": enroll,
        "rooms": [list(r) for r in rooms],
        "room_blockouts": blockouts,
        "_per_crn": per_crn,
        "_rooms": rooms,
    }


def write_csvs(out: str, data: dict) -> None:
    os.makedirs(out, exist_ok=True)
    files = {
        "courses.csv": (
            [
                "CRN",
                "CourseID",
                "Enrollment",
                "Instructor Name",
                "department",
                "examination_term",
            ],
            data["courses"],
        ),
        "enrollments.csv": (["Student_PIDM", "CRN"], data["enrollments"]),
        "rooms.csv": (["Room", "Capacity"], data["rooms"]),
        "room_blockouts.csv": (["Room", "Day", "Block"], data["room_blockouts"]),
    }
    for name, (header, rows) in files.items():
        with open(os.path.join(out, name), "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(header)
            w.writerows(rows)


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--students", type=int, default=5000)
    ap.add_argument("--courses", type=int, default=400)
    ap.add_argument("--rooms", type=int, default=35)
    ap.add_argument(
        "--clique-size",
        type=int,
        default=16,
        help="courses per program; controls conflict-graph clique size",
    )
    ap.add_argument(
        "--avg-load", type=float, default=3.6, help="mean courses per student"
    )
    ap.add_argument(
        "--gen-eds", type=int, default=6, help="shared cross-program courses"
    )
    ap.add_argument(
        "--min-size", type=int, default=5, help="minimum enrollment per course"
    )
    ap.add_argument(
        "--blockouts", type=int, default=5, help="number of (room, day, block) rows"
    )
    ap.add_argument("--seed", type=int, default=4535)
    ap.add_argument("--out", default="sample_data_large")
    args = ap.parse_args()

    data = build_dataset(args)
    write_csvs(args.out, data)

    sizes = sorted(data["_per_crn"].values())
    max_cap = max(cap for _, cap in data["_rooms"])
    print(f"wrote {args.out}/  (seed={args.seed})")
    print(
        f"  courses={len(data['courses'])} students={args.students} "
        f"enroll_rows={len(data['enrollments'])} "
        f"avg_load={len(data['enrollments']) / args.students:.2f}"
    )
    print(
        f"  class size min/median/mean/max="
        f"{sizes[0]}/{statistics.median(sizes):.0f}/{statistics.mean(sizes):.1f}/{sizes[-1]}"
    )
    print(
        f"  rooms={len(data['_rooms'])} max_capacity={max_cap} "
        f"blockouts={len(data['room_blockouts'])}"
    )


if __name__ == "__main__":
    main()
