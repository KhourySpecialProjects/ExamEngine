export interface DatasetMetadata {
  dataset_id: string;
  dataset_name: string;
  created_at: string;
  files: {
    courses: CoursesFileMetadata;
    enrollments: EnrollmentsFileMetadata;
    rooms: RoomsFileMetadata;
    room_blockouts?: RoomBlockoutsFileMetadata;
    combined_exams?: CombinedExamsFileMetadata;
    common_exams?: CommonExamsFileMetadata;
  };
  status: string;
}

export interface BaseFileMetadata {
  filename: string;
  rows: number;
  columns: string[];
  size_bytes: number;
}

export interface CoursesFileMetadata extends BaseFileMetadata {
  unique_crns: number;
  total_students: number;
  avg_class_size: number;
  subjects: number;
}

export interface EnrollmentsFileMetadata extends BaseFileMetadata {
  unique_students: number;
  unique_crns: number;
  total_enrollments: number;
}

export interface RoomsFileMetadata extends BaseFileMetadata {
  unique_rooms: number;
  total_capacity: number;
  avg_capacity: number;
  max_capacity: number;
}

export interface RoomBlockoutsFileMetadata extends BaseFileMetadata {
  unique_rooms_blocked: number;
  total_blockout_entries: number;
}

export interface OverCapacityCombinedExam {
  group: string;
  total_enrollment: number;
  max_room_capacity: number;
}

export interface CombinedExamsFileMetadata extends BaseFileMetadata {
  exam_groups: number;
  merged_crns: number;
  over_capacity_groups?: OverCapacityCombinedExam[];
}

export interface InfeasibleCommonGroup {
  group: string;
  reason: string;
}

export interface StudentOverlapCommonGroup {
  group: string;
  students: number;
}

export interface CommonExamsFileMetadata extends BaseFileMetadata {
  common_groups: number;
  common_crns: number;
  infeasible_groups?: InfeasibleCommonGroup[];
  student_overlap_groups?: StudentOverlapCommonGroup[];
}
