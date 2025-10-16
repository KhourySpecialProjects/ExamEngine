import pandas as pd

def export_student_schedule(g_backend, enrollment_df, df_schedule,
                            base_name="student_schedule",
                            max_exams_in_wide=12):
    """
    Creates two files:
      - {base_name}_long.csv : one row per student-exam with separate columns
      - {base_name}_wide.csv : one row per student, columns 'Exam 1'...'Exam K'
                               each cell is a compact metadata string

    Required:
      - g_backend.assignment  (CRN -> (day_idx, block_idx)) already populated
      - df_schedule from g_backend.assign_rooms() with:
          ['CRN','Course','Day','Block','Room','Capacity','Size','Valid']
      - enrollment_df with ['student_id','CRN'] (clean/registered only)
    """
    # ensure minimal columns
    enroll = enrollment_df[["student_id", "CRN"]].drop_duplicates().copy()
    meta = df_schedule.set_index("CRN").to_dict(orient="index")  # CRN -> dict

    long_rows = []
    for sid, grp in enroll.groupby("student_id"):
        # collect this student's scheduled exams (skip CRNs not in assignment)
        items = []
        for crn in grp["CRN"]:
            if crn in g_backend.assignment and crn in meta:
                day_idx, block_idx = g_backend.assignment[crn]
                info = meta[crn]
                items.append((day_idx, block_idx, crn, info))
        # sort by day, then block
        items.sort(key=lambda x: (x[0], x[1]))

        # build long-form rows
        for i, (_, _, crn, info) in enumerate(items, 1):
            long_rows.append({
                "student_id": sid,
                "exam_num": i,
                "CRN": crn,
                "Course": info.get("Course", ""),
                "Day": info.get("Day", ""),
                "Block": info.get("Block", ""),
                "Room": info.get("Room", ""),
                "Capacity": info.get("Capacity", ""),
                "Size": info.get("Size", ""),
                "Valid": info.get("Valid", "")
            })

    long_df = pd.DataFrame(long_rows)
    long_path = f"{base_name}_long.csv"
    long_df.to_csv(long_path, index=False)

    # wide format: Exam 1..K columns with compact metadata string
    wide_rows = []
    for sid, sdf in long_df.groupby("student_id"):
        sdf = sdf.sort_values(["Day", "Block", "exam_num"])
        row = {"student_id": sid}
        for i, r in enumerate(sdf.itertuples(index=False), 1):
            row[f"Exam {i}"] = (
                f"{r.CRN} | {r.Course} | {r.Day} {r.Block} | "
                f"{r.Room} | cap {r.Capacity} | size {r.Size} | valid {r.Valid}"
            )
            if i >= max_exams_in_wide:
                break
        wide_rows.append(row)

    wide_df = pd.DataFrame(wide_rows).sort_values("student_id")
    wide_path = f"{base_name}_wide.csv"
    wide_df.to_csv(wide_path, index=False)

    print(f"Saved: {long_path}  (rows: {len(long_df)})")
    print(f"Saved: {wide_path} (students: {len(wide_df)})")
    return long_df, wide_df
