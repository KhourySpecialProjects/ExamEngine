#!/usr/bin/env python3
"""Generate a coherent, tunable exam-scheduling test dataset.

Emits CSVs matching the upload schema:
    courses.csv, enrollments.csv, rooms.csv, room_blockouts.csv
and, when requested:
    combined_exams.csv  (ExamGroup,CRN)    - sections sharing one exam and room
    common_exams.csv    (Common_Group,CRN) - sections sharing one time block,
                                             each combined group / lone CRN in
                                             its own room

Enrollment is modeled as independent "program" cliques rather than uniform
random assignment: each student belongs to one program and draws most of their
courses from it, with a small shared gen-ed pool bridging programs. Disjoint
programs can reuse the same time slots, so the conflict graph has realistic
density (its chromatic number tracks the clique size, not the course count).
Class sizes come out right-skewed, and each course's declared Enrollment equals
its actual number of enrollment rows.

Multi-section courses (--sectioned-courses) add extra CRNs that share a base
course's code; a student taking that course is placed in exactly one section,
so sections of one course never share students. Common groups are drawn from
those sections (e.g. 4 of 6 BIOL sections); some contain a combined pair
(common + combined). Every common group is guaranteed to fit the room inventory
in an otherwise empty block. Standalone combined groups pair unused sibling
sections or, failing that, unrelated unused CRNs (cross-listing). With
--oversize-combined, extra combined groups exceed the largest room so the
unscheduled path is exercised.

Deterministic for a given --seed. With all group/section options at their
defaults (0), output is identical to earlier versions of this script. Output is
regenerable, so the output dir is gitignored rather than committed. Examples:

    python backend/script/gen_test_data.py \\
        --students 5000 --courses 400 --rooms 35 --seed 4535 --out sample_data_large

    python backend/script/gen_test_data.py \\
        --students 8000 --courses 600 --rooms 75 --max-capacity 400 \\
        --sectioned-courses 90 --common-groups 35 --combined-groups 30 \\
        --oversize-combined 1 --blockouts 25 --out sample_data_xl

Unroomed exams require enough --blockouts that every room is blocked at some
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


def fits_rooms(unit_sizes: list[int], capacities: list[int]) -> bool:
    """True if every unit gets its own room: largest unit into smallest fit."""
    free = sorted(capacities)
    for size in sorted(unit_sizes, reverse=True):
        room = next((i for i, cap in enumerate(free) if cap >= size), None)
        if room is None:
            return False
        free.pop(room)
    return True


def build_dataset(args: argparse.Namespace) -> dict[str, list]:
    rng = random.Random(args.seed)  # noqa: S311 - deterministic test data, not crypto
    # Separate stream for section work so the base dataset (programs, loads,
    # rooms) stays identical to a run without sections.
    srng = random.Random(args.seed + 1)  # noqa: S311

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
    base_crns = [c[0] for c in courses]

    # Shared gen-ed pool: one course from every few programs.
    step = max(1, n_prog // max(1, args.gen_eds))
    gen_pool = [prog_courses[p][0] for p in range(0, n_prog, step)][: args.gen_eds]
    if not gen_pool:
        gen_pool = base_crns[: args.gen_eds]

    faculty = {
        p: [f"Dr. {chr(65 + (p % 26))}{j}" for j in range(1, 7)] for p in range(n_prog)
    }
    instr_of = {c: rng.choice(faculty[p]) for c, _, _, p in courses}

    # Extra sections: new CRNs (after all base CRNs) sharing a base course code.
    sections: dict[str, list[str]] = {c: [c] for c in base_crns}
    offering_of: dict[str, str] = {c: c for c in base_crns}
    if args.sectioned_courses:
        meta = {c: (code, dept, p) for c, code, dept, p in courses}
        picks = srng.sample(base_crns, min(args.sectioned_courses, len(base_crns)))
        for base in sorted(picks):
            code, dept, p = meta[base]
            n_sections = srng.randint(args.sections_min, args.sections_max)
            for _ in range(n_sections - 1):
                c = str(crn)
                crn += 1
                courses.append((c, code, dept, p))
                sections[base].append(c)
                offering_of[c] = base
                instr_of[c] = srng.choice(faculty[p])
    all_crns = [c[0] for c in courses]

    # Load distribution weighted toward the requested average.
    weights = [max(0.05, 1 - abs(load - args.avg_load) / 3) for load in LOADS]

    per_crn: dict[str, int] = defaultdict(int)
    enroll: list[tuple[str, str]] = []
    offerings_of_student: dict[str, set[str]] = defaultdict(set)
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
        for offering in sorted(picked):
            secs = sections[offering]
            c = secs[0] if len(secs) == 1 else srng.choice(secs)
            enroll.append((sid, c))
            per_crn[c] += 1
            offerings_of_student[sid].add(offering)

    # Floor tiny courses so none are empty. A student never lands in two
    # sections of the same multi-section course.
    for c in all_crns:
        multi = len(sections[offering_of[c]]) > 1
        while per_crn[c] < args.min_size:
            sid = f"{100000 + rng.randint(1, args.students):09d}"
            if multi and offering_of[c] in offerings_of_student[sid]:
                continue
            enroll.append((sid, c))
            per_crn[c] += 1
            offerings_of_student[sid].add(offering_of[c])

    rooms = build_rooms(args.rooms, rng, args.max_capacity)
    small_rooms = [r for r, cap in rooms if cap < 120] or [r for r, _ in rooms]
    blockouts = [
        [rng.choice(small_rooms), rng.randrange(DAYS), rng.randrange(BLOCKS)]
        for _ in range(args.blockouts)
    ]

    code_of = {c: code for c, code, _, _ in courses}
    combined, common = build_groups(
        args, sections, code_of, per_crn, [cap for _, cap in rooms]
    )

    course_rows = [
        [c, code, per_crn[c], instr_of[c], dept, TERM] for c, code, dept, _ in courses
    ]
    return {
        "courses": course_rows,
        "enrollments": enroll,
        "rooms": [list(r) for r in rooms],
        "room_blockouts": blockouts,
        "combined_exams": combined,
        "common_exams": common,
        "_per_crn": per_crn,
        "_rooms": rooms,
    }


def build_groups(
    args: argparse.Namespace,
    sections: dict[str, list[str]],
    code_of: dict[str, str],
    per_crn: dict[str, int],
    capacities: list[int],
) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    """Pick combined and common groups that pass upload validation.

    Returns (combined, common): label -> CRNs as they will be written. Common
    groups sometimes list only one member of an inner combined group, so the
    closure rule gets exercised.
    """
    grng = random.Random(args.seed + 2)  # noqa: S311
    max_cap = max(capacities)
    combined: dict[str, list[str]] = {}
    common: dict[str, list[str]] = {}
    used: set[str] = set()

    multi = sorted(base for base, secs in sections.items() if len(secs) > 1)
    grng.shuffle(multi)

    for base in multi:
        if len(common) >= args.common_groups:
            break
        secs = sections[base]
        # Most, not necessarily all, sections sit the common exam (e.g. 4 of 6).
        k = grng.randint(len(secs) // 2 + 1, len(secs)) if len(secs) > 2 else 2
        members = sorted(grng.sample(secs, k))
        units: list[list[str]] = [[c] for c in members]
        inner: list[str] | None = None
        if len(members) >= 3 and grng.random() < args.common_combined_rate:
            pair = grng.sample(members, 2)
            if sum(per_crn[c] for c in pair) <= max_cap:
                inner = sorted(pair)
                units = [inner] + [[c] for c in members if c not in pair]
        # Shrink until the group fits the room inventory at once.
        while len(units) >= 2 and not fits_rooms(
            [sum(per_crn[c] for c in u) for u in units], capacities
        ):
            singles = [u for u in units if len(u) == 1]
            if not singles:
                break
            units.remove(max(singles, key=lambda u: per_crn[u[0]]))
        if len(units) < 2 or not fits_rooms(
            [sum(per_crn[c] for c in u) for u in units], capacities
        ):
            continue

        code = code_of[base]
        listed: list[str] = []
        for unit in units:
            if unit is inner:
                combined[f"{code} Combined"] = inner
                # List one member only some of the time (closure rule).
                listed.extend(inner if grng.random() < 0.7 else inner[:1])
            else:
                listed.extend(unit)
        common[f"{code} Common Final"] = sorted(listed)
        used.update(c for u in units for c in u)

    def free_pair_sources() -> list[list[str]]:
        sibs = []
        for base in multi:
            free = [c for c in sections[base] if c not in used]
            if len(free) >= 2:
                sibs.append(free)
        return sibs

    xl = 0
    standalone = 0
    while standalone < args.combined_groups:
        sources = free_pair_sources()
        if sources:
            free = grng.choice(sources)
            pair = sorted(grng.sample(free, 2))
            label = f"{code_of[pair[0]]} Sections {'+'.join(pair)}"
        else:
            free_all = sorted(c for c in per_crn if c not in used)
            if len(free_all) < 2:
                break
            pair = sorted(grng.sample(free_all, 2))
            xl += 1
            label = f"Cross-list {xl:02d}"
        if sum(per_crn[c] for c in pair) > max_cap:
            used.update(pair)  # skip; never retry the same oversized pair
            continue
        combined[label] = pair
        used.update(pair)
        standalone += 1

    # Deliberately oversized combined groups (reported, left unscheduled). Built
    # from CRNs that each fit a room, so it is the merge that overflows.
    by_size = sorted(
        (c for c in per_crn if c not in used and per_crn[c] <= max_cap),
        key=per_crn.get,
    )
    for n in range(1, args.oversize_combined + 1):
        group: list[str] = []
        while by_size and sum(per_crn[c] for c in group) <= max_cap:
            group.append(by_size.pop())
        if len(group) < 2 or sum(per_crn[c] for c in group) <= max_cap:
            break
        combined[f"Oversize Combined {n:02d}"] = sorted(group)
        used.update(group)

    return combined, common


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
    group_files = {
        "combined_exams.csv": ("ExamGroup", data["combined_exams"]),
        "common_exams.csv": ("Common_Group", data["common_exams"]),
    }
    for name, (column, groups) in group_files.items():
        if groups:
            rows = [[label, c] for label, crns in groups.items() for c in crns]
            files[name] = ([column, "CRN"], rows)
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
    ap.add_argument("--courses", type=int, default=400, help="distinct courses")
    ap.add_argument("--rooms", type=int, default=35)
    ap.add_argument(
        "--max-capacity", type=int, default=250, help="size of the largest hall"
    )
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
    ap.add_argument(
        "--sectioned-courses",
        type=int,
        default=0,
        help="courses split into multiple sections (extra CRNs, same code)",
    )
    ap.add_argument("--sections-min", type=int, default=2)
    ap.add_argument("--sections-max", type=int, default=6)
    ap.add_argument(
        "--common-groups",
        type=int,
        default=0,
        help="common exam groups (same block, separate rooms); needs sections",
    )
    ap.add_argument(
        "--common-combined-rate",
        type=float,
        default=0.4,
        help="share of common groups containing a combined pair",
    )
    ap.add_argument(
        "--combined-groups",
        type=int,
        default=0,
        help="standalone combined groups (same block and room)",
    )
    ap.add_argument(
        "--oversize-combined",
        type=int,
        default=0,
        help="combined groups larger than the biggest room (left unscheduled)",
    )
    ap.add_argument("--seed", type=int, default=4535)
    ap.add_argument("--out", default="sample_data_large")
    args = ap.parse_args()
    if not 2 <= args.sections_min <= args.sections_max:
        ap.error("need 2 <= --sections-min <= --sections-max")

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
    combined, common = data["combined_exams"], data["common_exams"]
    if combined or common:
        inner = sum(1 for k in combined if k.endswith(" Combined"))
        oversize = sum(1 for k in combined if k.startswith("Oversize"))
        print(
            f"  combined_groups={len(combined)} (inside common={inner}, "
            f"oversize={oversize}) common_groups={len(common)} "
            f"common_crns={sum(len(v) for v in common.values())}"
        )


if __name__ == "__main__":
    main()
