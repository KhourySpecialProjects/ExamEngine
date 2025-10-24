# Data Filtering Script Documentation

## Overview
The `data_filtering.py` script processes and cleans data files to create three output CSV files for the ExamEngine system.

## Input Files
- `Fall2025FinalExams.csv` - Final exam schedule data
- `DB_ST_Class-Census ExamEngine_20250919_105424.csv` - Class census data with room information
- `DB_ST_Enrollment-Census ExamEngine_20250919_113535.csv` - Student enrollment data
- `SpListing.xlsx.csv` - Classroom/room listing data

## Output Files

### 1. final_classrooms.csv
- **Source**: SpListing.xlsx.csv
- **Columns**: 
  - `room_name` (renamed from "Location Formal Name")
  - `capacity` (renamed from "Capacity")
- **Records**: 270 classroom records

### 2. final_classcensus.csv
- **Source**: Fall2025FinalExams.csv + DB_ST_Class-Census (merged)
- **Columns**:
  - `CRN` - Course Reference Number
  - `CourseID` - Course Identification
  - `num_students` (renamed from "Enrolled")
  - `building` - Building code from Class-Census
  - `room_number` - Room number from Class-Census
- **Filters Applied**:
  - Removed Oakland classes (Campus != 'OAK')
  - Removed classes with 0 students
  - Matched CRNs between Fall2025FinalExams and Class-Census (202610 academic period)
- **Records**: 1,161 class records

### 3. final_enrollment.csv
- **Source**: DB_ST_Enrollment-Census
- **Columns**:
  - `Student_PIDM` - Student identifier
  - `CRN` - Course Reference Number
  - `Instructor Name` - Instructor name
- **Filters Applied**:
  - Academic period 202610 only
  - CRNs must exist in Fall2025FinalExams
- **Records**: 42,849 enrollment records

## Processing Summary

### Data Filtering Results:
- **Fall2025FinalExams**: 1,252 → 1,161 records (removed 68 Oakland + 19 zero-enrollment classes)
- **Class-Census**: 11,257 → 1,062 records (filtered for 202610 period and matching CRNs)
- **Enrollments**: 104,674 → 42,849 records (filtered for 202610 period and matching CRNs)
- **SpListing**: 272 → 270 records (cleaned classroom data)

### Room Information Matching:
- All 1,161 classes successfully matched with room information from Class-Census
- 0 classes without room information

## Usage
```bash
cd Data
python data_filtering.py
```

The script will automatically process all input files and generate the three output CSV files in the same directory.

## Current Algorithm Usage
The ExamEngine scheduling algorithms currently use these final data files:
- `final_classcensus.csv` - Course and enrollment data
- `final_enrollment.csv` - Student enrollment and instructor data  
- `final_classrooms.csv` - Classroom capacity data

These files are referenced in the backend test files and validation scripts.
