# Data Guide

CSV file formats, database management, and data operations for ExamEngine.

## CSV File Formats

ExamEngine requires three CSV files — **courses**, **enrollments**, and **rooms** — to generate exam schedules, plus an optional **room blockouts** file. Column names are auto-detected from multiple aliases (case-insensitive, whitespace-trimmed).

> **Required vs optional:** ✅ = required (the upload is rejected if the column is missing). ❌ = optional (used if present, ignored if absent). Any column not listed below is ignored. For courses/enrollments/rooms a row with a missing/invalid *required* value aborts the entire import; invalid room-blockout rows are skipped individually.

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

## Data Validation

The system automatically:

- Detects column names from aliases (case-insensitive)
- Cleans whitespace and formats
- Converts numeric strings (e.g., "11310.0" → "11310")
- Rejects the entire upload if a required column is missing or a required value is empty/invalid (courses, enrollments, rooms); invalid room-blockout rows are skipped individually
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

## S3 Storage Structure

Datasets are stored in S3 with the following structure:

```
s3://examengine-datasets/
└── {dataset_uuid}/
    ├── courses.csv
    ├── enrollments.csv
    └── rooms.csv
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
