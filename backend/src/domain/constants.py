from dataclasses import dataclass
from datetime import time


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


@dataclass(frozen=True)
class ExamBlock:
    """One exam block of a day; its index in EXAM_BLOCKS is the block index."""

    start: time
    end: time
    label: str


# The only definition of the exam blocks. Engines use block indices; the clock
# times and labels are what the app stores and shows.
EXAM_BLOCKS = (
    ExamBlock(time(8, 0), time(10, 0), "8AM-10AM"),
    ExamBlock(time(10, 30), time(12, 30), "10:30AM-12:30PM"),
    ExamBlock(time(13, 0), time(15, 0), "1PM-3PM"),
    ExamBlock(time(15, 30), time(17, 30), "3:30PM-5:30PM"),
    ExamBlock(time(18, 0), time(20, 0), "6PM-8PM"),
)
BLOCK_TIMES = {index: block.label for index, block in enumerate(EXAM_BLOCKS)}

# The wrong blocks the app used before they were corrected, same indices. Kept
# to relabel saved data at startup and to read room blockout files naming them.
LEGACY_EXAM_BLOCKS = (
    ExamBlock(time(9, 0), time(11, 0), "9AM-11AM"),
    ExamBlock(time(11, 30), time(13, 30), "11:30AM-1:30PM"),
    ExamBlock(time(14, 0), time(16, 0), "2PM-4PM"),
    ExamBlock(time(16, 30), time(18, 30), "4:30PM-6:30PM"),
    ExamBlock(time(19, 0), time(21, 0), "7PM-9PM"),
)

BLOCKS_PER_DAY = 5
LARGE_COURSE_THRESHOLD = 100
EARLY_WEEK_CUTOFF = 3  # Wednesday
CONFLICT_TYPE_LABELS = {
    "student_double_book": "Student Double-Booked",
    "instructor_double_book": "Instructor Double-Booked",
    "student_gt_max_per_day": "Student Over Daily Limit",
    "instructor_gt_max_per_day": "Instructor Over Daily Limit",
}
