# Constants
DAY_NAMES = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]
BLOCK_TIMES = {
    0: "9AM-11AM",
    1: "11:30AM-1:30PM",
    2: "2PM-4PM",
    3: "4:30PM-6:30PM",
    4: "7PM-9PM",
}

BLOCKS_PER_DAY = 5
LARGE_COURSE_THRESHOLD = 100
EARLY_WEEK_CUTOFF = 3  # Wednesday
CONFLICT_TYPE_LABELS = {
    "student_double_book": "Student Double-Booked",
    "instructor_double_book": "Instructor Double-Booked",
    "student_gt_max_per_day": "Student Over Daily Limit",
    "instructor_gt_max_per_day": "Instructor Over Daily Limit",
}
