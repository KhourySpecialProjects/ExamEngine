# Data Guide

CSV file formats, database management, and data operations for ExamEngine.

## CSV File Formats

ExamEngine requires three CSV files — **courses**, **enrollments**, and **rooms** — to generate exam schedules, plus three optional files: **room blockouts**, **combined exams**, and **common exams**. All files are uploaded together in one `POST /api/datasets/upload` request (multipart form fields `courses`, `enrollments`, `rooms`, `room_blockouts`, `combined_exams`, `common_exams`). Column names are auto-detected from multiple aliases (case-insensitive, whitespace-trimmed).

> **Required vs optional:** ✅ = required (the upload is rejected if the column is missing). ❌ = optional (used if present, ignored if absent). Any column not listed below is ignored. For courses/enrollments/rooms/combined exams/common exams a row with a missing/invalid *required* value aborts the entire import; invalid room-blockout rows are skipped individually.

### courses.csv

Contains course/section information. One row per CRN — if a CRN appears on multiple rows the file is de-duplicated by CRN and only the last row is kept.

| Column           | Required | Accepted Names                                                                                                 | Description                                     |
| ---------------- | -------- | ------------------------------------------------------------------------------------------------------------- | ----------------------------------------------- |
| crn              | ✅       | `Course_Reference_Number`, `CRN`, `Course Registration Number`, `crn`                                         | Unique course/section identifier                |
| course_code      | ✅       | `Course_Identification`, `CourseID`, `Course ID`, `Course Code`, `course_subject_code`, `course_code`         | e.g., "CS 4535"                                 |
| enrollment_count | ✅       | `Total_Enrollment`, `Enrollment`, `num_students`, `Student Count`, `Size`, `UG_Enrollment`, `enrollment_count` | Number of students (must be a positive integer) |
| instructor_name  | ❌       | `Primary_Instructor_PIDM`, `Instructor Name`, `Instructor`, `Faculty Name`, `Professor`, `instructor_name`    | Instructor's name                               |
| department       | ❌       | `Course_Department_Code`, `Course_Department_Desc`, `department`, `dept`                                       | Department code, e.g., "CSCI"                   |
| examination_term | ❌       | `Academic_Period_NUFreeze`, `Academic_Period`, `exam_term`, `examination_term`                                | e.g., "Fall 2025"                               |

> If `instructor_name` is absent (or blank on a row), that section is excluded from all instructor constraints — the scheduler will not track faculty exams-per-day or instructor back-to-back for it.

**Example:**

```csv
CRN,CourseID,Enrollment,Instructor Name,department,examination_term
11310,CS 3500,150,Dr. Smith,CSCI,Fall 2025
11311,CS 4535,45,Dr. Johnson,CSCI,Fall 2025
```

### enrollments.csv

Maps students to the courses they're enrolled in. Only these two columns are read; any others are ignored.

| Column     | Required | Accepted Names                                                                       | Description                     |
| ---------- | -------- | ----------------------------------------------------------------------------------- | ------------------------------- |
| student_id | ✅       | `Student_PIDM`, `Student ID`, `PIDM`, `Student Number`, `student_id`, `student_pidm` | Unique student identifier       |
| crn        | ✅       | `Course_Reference_Number`, `CRN`, `Course Registration Number`, `crn`               | Must match a CRN in courses.csv |

**Example:**

```csv
Student_PIDM,CRN
001234567,11310
001234567,11311
001234568,11310
```

### rooms.csv

Available exam rooms and their capacities.

| Column    | Required | Accepted Names                                                                                          | Description                        |
| --------- | -------- | ------------------------------------------------------------------------------------------------------ | ---------------------------------- |
| room_name | ✅       | `Location Name`, `Room`, `Room Name`, `Location`, `Building + Room`, `Location Formal Name`, `room_name` | Room identifier                    |
| capacity  | ✅       | `Capacity`, `Seats`, `Max Capacity`, `capacity`                                                         | Maximum seating (positive integer) |

**Example:**

```csv
Room,Capacity
Shillman 105,200
Ell Hall 312,75
Curry Student Center 440,150
```

### room_blockouts.csv (optional)

Marks specific (room, day, time-block) combinations as unavailable. This file is optional — omit it if there are no blockouts. All three columns are required; invalid rows are skipped individually rather than aborting the upload.

| Column | Required | Accepted Names                                               | Description                                         |
| ------ | -------- | ----------------------------------------------------------- | -------------------------------------------------- |
| Room   | ✅       | `Room`, `Location Name`, `Location`, `Room Name`, `room`, `room_name` | Room to block (should match a room in rooms.csv)   |
| Day    | ✅       | `Day`, `Weekday`, `day`, `day_index`, `Day Index`           | `0`–`6` (Monday = 0) or a day name, e.g., "Monday" |
| Block  | ✅       | `Block`, `Time Block`, `block`, `block_index`, `Block Index` | `0`–`4` or a time string, e.g., "9AM-11AM"         |

**Example:**

```csv
Room,Day,Block
Shillman 105,0,2
West Village H 212,Monday,9AM-11AM
```

### combined_exams.csv (optional)

Defines combined exams: groups of course sections (CRNs) merged into one exam — same time block **and same room**. Each group is a **merge group**, and the group label is its identifier. This file is optional — omit it if no sections share an exam. It uses long format, one row per (group, CRN); a group needs at least two rows. Cells are read as text, so labels such as `01` and `1` are different groups. Blank lines are ignored. Unlike room blockouts, any invalid row fails the whole upload (see the validation rules below).

| Column                  | Required | Accepted Names                                                                                        | Description                                               |
| ----------------------- | -------- | ---------------------------------------------------------------------------------------------------- | --------------------------------------------------------- |
| Exam_Group              | ✅       | `Exam_Group`, `ExamGroup`, `Exam Group`, `Common Exam`, `merge_group`, `merge_group_id`, `Group`, `group_id` | Group label (whitespace-trimmed), e.g., "MATH Common Final" |
| Course_Reference_Number | ✅       | `Course_Reference_Number`, `CRN`, `Course Registration Number`, `crn`                                | Must match a CRN in courses.csv                           |

**Example:**

```csv
ExamGroup,CRN
MATH Common Final,11315
MATH Common Final,11316
PHYS Common Final,11320
PHYS Common Final,11321
```

**Validation rules:**

| #   | Rule                                                                         | Result                                                                                           |
| --- | ---------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------ |
| V1  | A required column is missing                                                 | ❌ Upload rejected                                                                               |
| V2  | A row has a blank group or a blank CRN, or the CRN has a decimal part (e.g. `11316.9`) | ❌ Upload rejected (error lists the row numbers)                                       |
| V3  | The same CRN appears in two different groups                                 | ❌ Upload rejected                                                                               |
| V4  | A group has fewer than 2 distinct CRNs                                       | ❌ Upload rejected                                                                               |
| V5  | Exact duplicate (group, CRN) rows                                            | ✅ Accepted; duplicates are silently de-duplicated                                               |
| V6  | A CRN is not in courses.csv, or has zero enrollment there (the scheduler drops zero-enrollment sections) | ❌ Upload rejected                                                   |
| V7  | A group's combined enrollment exceeds the largest room in rooms.csv          | ⚠️ Warning only; the group is saved and reported in the upload response as `over_capacity_groups` |
| V8  | The file is empty, has no groups (header only), or is not a parseable CSV    | ❌ Upload rejected                                                                               |
| V9  | Two group labels differ only in capitalization or spacing (e.g. `MATH Final` / `math final`) | ❌ Upload rejected (likely a typo)                                               |

Problems within the file itself (V2–V5, V8, V9) are reported together. Checks against courses.csv and rooms.csv (V6, V7) run only once every file passes its own checks. A rejected upload returns HTTP 400 `{"message": "File validation failed", "errors": {"combined_exams": "<reason>"}}`, and nothing is stored. Over-capacity groups (V7) are saved but no room can hold them, so the scheduler reports them as unscheduled. The upload response reports the file under `files.combined_exams` as `{rows, exam_groups, merged_crns, over_capacity_groups}`.

Valid groups are stored in the `datasets.course_merges` JSONB column as `{group_label: [CRN, ...]}` (CRNs in order of first appearance), e.g., `{"MATH Common Final": ["11315", "11316"]}`. Combined groups can only be set by uploading this file; to change them, upload a new dataset. They are read back with `GET /api/datasets/{dataset_id}/merges` (the column and route keep their original "merges" names).

> Datasets uploaded before combined and common exams were split stored this file as `common_exams.csv` (file type `common_exams`, metadata with `exam_groups`). They are still reported as `combined_exams`.

### common_exams.csv (optional)

Defines common exams: groups of course sections (CRNs) that sit in the **same time block but in different rooms** (e.g. so exam content can't leak between sections). This file is optional and separate from combined_exams.csv. It uses the same long format and file-level rules as combined exams (text cells, blank lines ignored, duplicates de-duplicated, labels differing only in case/spacing rejected, at least 2 distinct CRNs per group), but a different group header, so a combined exam file uploaded in this slot is rejected rather than silently misread.

| Column                  | Required | Accepted Names                                                        | Description                                         |
| ----------------------- | -------- | --------------------------------------------------------------------- | --------------------------------------------------- |
| Common_Group            | ✅       | `Common_Group`, `CommonGroup`, `Common Group`, `common_group`          | Group label (whitespace-trimmed), e.g., "BIOL 1101 Final" |
| Course_Reference_Number | ✅       | `Course_Reference_Number`, `CRN`, `Course Registration Number`, `crn` | Must match a CRN in courses.csv                     |

**Example:**

```csv
Common_Group,CRN
BIOL 1101 Final,11111
BIOL 1101 Final,33333
BIOL 1101 Final,44444
```

**Combined groups inside a common group (closure rule):** if a CRN listed in a common group belongs to a combined group, the entire combined group belongs to that common group and still shares one room. Listing one or all members of the combined group is equivalent. Each combined group or lone CRN is a **room unit** that gets its own room. With combined group `{11111, 22222}`, the example above schedules one time block with three rooms: 11111+22222, 33333, and 44444.

**Validation rules** (in addition to the file-level rules V1–V5, V8, V9 above, with "group" meaning common group):

| #   | Rule                                                                                         | Result                                                                                                          |
| --- | -------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| C1  | The same CRN appears in two different common groups                                           | ❌ Upload rejected                                                                                              |
| C2  | A CRN is not in courses.csv, or has zero enrollment there                                     | ❌ Upload rejected                                                                                              |
| C3  | Members of one combined group are listed in different common groups                           | ❌ Upload rejected                                                                                              |
| C4  | A common group has fewer than 2 room units after the closure rule (e.g. it only lists members of one combined group) | ❌ Upload rejected                                                                       |
| C5  | The group's room units can't all be seated at once (each in its own room; largest unit first into the smallest room that fits, over all rooms, ignoring blockouts) | ⚠️ Saved; reported as `infeasible_groups: [{group, reason}]`. The scheduler leaves the **whole** group unscheduled |
| C6  | A student is enrolled in 2+ room units of the same common group                                | ⚠️ Saved; reported as `student_overlap_groups: [{group, students}]` (those students have simultaneous exams)    |

Cross-file checks (C2–C4) run once every file passes its own checks; errors in combined_exams.csv and common_exams.csv are reported together, e.g. HTTP 400 `{"message": "File validation failed", "errors": {"common_exams": "<reason>"}}`. The upload response reports the file under `files.common_exams` as `{rows, common_groups, common_crns, infeasible_groups, student_overlap_groups}`.

Valid groups are stored, as listed (closure is applied at scheduling time), in the nullable `datasets.common_exam_groups` JSONB column as `{group_label: [CRN, ...]}`. The scheduler places common groups before all other exams; a group is never split across blocks or partially placed. Common groups can only be set by uploading this file; to change them, upload a new dataset. They are read back with `GET /api/datasets/{dataset_id}/common-exams`.

## Data Validation

The system automatically:

- Detects column names from aliases (case-insensitive)
- Cleans whitespace and formats
- Converts numeric strings (e.g., "11310.0" → "11310")
- Rejects the entire upload if a required column is missing or a required value is empty/invalid (courses, enrollments, rooms, combined exams, common exams); invalid room-blockout rows are skipped individually
- Reports validation errors with row numbers

### Common Validation Errors

| Error                                      | Cause                         | Fix                       |
| ------------------------------------------ | ----------------------------- | ------------------------- |
| "Missing CRN"                              | Empty or null CRN value       | Ensure all rows have CRN  |
| "CSV columns don't match any known schema" | Column names not recognized   | Use accepted column names |
| "Enrollment count cannot be negative"      | Negative number in enrollment | Fix data or remove row    |

## Database Operations

### Local Development

```bash
# Reset database (drops all tables, recreates schema)
cd backend
python src/schemas/reset_database.py

# Or via Docker
docker-compose --profile dev exec backend-dev python src/schemas/reset_database.py
```

### Database Schema

<img src="figures/db_schemas.svg" alt="Database Schema Diagram" width="1000"/>

`datasets.common_exam_groups` (nullable JSONB) was added after the initial schema. `init_db` adds it on startup to existing Postgres databases with `ALTER TABLE datasets ADD COLUMN IF NOT EXISTS common_exam_groups JSONB DEFAULT NULL` (idempotent; no data migration needed).

## S3 Storage Structure

Datasets are stored in S3 with the following structure:

```
s3://examengine-datasets/
└── {dataset_uuid}/
    ├── courses.csv
    ├── enrollments.csv
    ├── rooms.csv
    ├── room_blockouts.csv   # only if uploaded
    ├── combined_exams.csv   # only if uploaded
    └── common_exams.csv     # only if uploaded
```

Files are private (no public access) and accessed via IAM roles.

## Troubleshooting

### "Dataset already exists"

A dataset with the same name exists. Use a unique name or delete the existing one.

### "CRN not found in courses"

Enrollment file references a CRN that doesn't exist in courses file. Ensure CRNs match exactly.

### Large file uploads timing out

For very large files (>50MB), consider:

- Splitting enrollments by term
- Removing historical/inactive courses
- Increasing upload timeout in nginx config in (dev environment)
