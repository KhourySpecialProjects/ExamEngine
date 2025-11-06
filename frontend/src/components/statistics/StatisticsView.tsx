"use client";

import { useMemo } from "react";
import {
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useScheduleStore } from "@/lib/store/scheduleStore";
import {
  BookOpen,
  Users,
  AlertTriangle,
  Building2,
  Calendar,
  TrendingUp,
  Clock,
} from "lucide-react";

const COLORS = {
  primary: "#3b82f6",
  success: "#10b981",
  warning: "#f59e0b",
  danger: "#ef4444",
  info: "#6366f1",
};

const CONFLICT_COLORS = [
  "#ef4444", // Student double-book
  "#f59e0b", // Student per-day limit
  "#8b5cf6", // Instructor double-book
  "#ec4899", // Instructor per-day limit
];

interface ConflictData {
  name: string;
  value: number;
}

export function StatisticsView() {
  const currentSchedule = useScheduleStore((state) => state.currentSchedule);

  const stats = useMemo(() => {
    if (!currentSchedule) return null;

    const schedule = currentSchedule.schedule;
    const summary = currentSchedule.summary;
    const conflicts = currentSchedule.conflicts;

    // Calculate exams per day
    const examsPerDay: Record<string, number> = {};
    const studentsPerDay: Record<string, number> = {};
    const timeBlocks: Record<string, number> = {};

    schedule.complete.forEach((exam) => {
      examsPerDay[exam.Day] = (examsPerDay[exam.Day] || 0) + 1;
      studentsPerDay[exam.Day] =
        (studentsPerDay[exam.Day] || 0) + (exam.Size || 0);
      timeBlocks[exam.Block] = (timeBlocks[exam.Block] || 0) + 1;
    });

    // Calculate room utilization - average across all exam-room assignments
    // This calculates utilization per exam (students/capacity) and averages them
    let totalUtilization = 0;
    let examCount = 0;

    schedule.complete.forEach((exam) => {
      // Ensure Capacity and Size are numbers
      const capacity = Number(exam.Capacity) || 0;
      const size = Number(exam.Size) || 0;

      if (capacity > 0) {
        const utilization = Math.min((size / capacity) * 100, 100); // Cap at 100%
        totalUtilization += utilization;
        examCount += 1;
      }
    });

    const roomUtilization = examCount > 0 ? totalUtilization / examCount : 0;

    // Calculate conflict breakdown - only include hard conflicts (not back-to-back warnings)
    const conflictBreakdown: ConflictData[] = [];
    const conflictTypes: Record<string, number> = {};

    // Process conflicts from breakdown - filter out back-to-back warnings for pie chart
    if (conflicts.breakdown && Array.isArray(conflicts.breakdown)) {
      conflicts.breakdown.forEach((conflict: any) => {
        const type = conflict.conflict_type || conflict.violation || "unknown";
        // Only count hard conflicts (exclude back-to-back which are soft warnings)
        if (
          type !== "back_to_back" &&
          type !== "back_to_back_student" &&
          type !== "back_to_back_instructor"
        ) {
          conflictTypes[type] = (conflictTypes[type] || 0) + 1;
        }
      });
    }

    // If no conflicts found in breakdown but real_conflicts > 0, create a placeholder
    // This handles the case where conflicts exist but aren't in the breakdown array
    if (Object.keys(conflictTypes).length === 0 && summary.real_conflicts > 0) {
      conflictTypes["unknown"] = summary.real_conflicts;
      // Debug: log this issue
      console.warn(
        `Conflict mismatch: ${summary.real_conflicts} conflicts reported but ${conflicts.breakdown.length} items in breakdown.`,
        "Breakdown items:",
        conflicts.breakdown,
      );
    }

    // Map conflict types to readable names
    const conflictTypeMap: Record<string, string> = {
      student_double_book: "Student Double-Book",
      student_gt_max_per_day: "Student Per-Day Limit",
      instructor_double_book: "Instructor Double-Book",
      instructor_gt_max_per_day: "Instructor Per-Day Limit",
      back_to_back: "Back-to-Back",
      back_to_back_student: "Back-to-Back (Students)",
      back_to_back_instructor: "Back-to-Back (Instructors)",
      unknown: "Uncategorized Conflicts",
    };

    Object.entries(conflictTypes).forEach(([type, count]) => {
      if (count > 0) {
        conflictBreakdown.push({
          name: conflictTypeMap[type] || type,
          value: count,
        });
      }
    });

    // Prepare data for charts
    const dayData = Object.entries(examsPerDay)
      .map(([day, count]) => ({
        name: day,
        exams: count,
      }))
      .sort((a, b) => {
        const dayOrder = [
          "Monday",
          "Tuesday",
          "Wednesday",
          "Thursday",
          "Friday",
          "Saturday",
          "Sunday",
        ];
        return dayOrder.indexOf(a.name) - dayOrder.indexOf(b.name);
      });

    // Prepare students per day data for pie chart
    const studentsPerDayData = Object.entries(studentsPerDay)
      .map(([day, count]) => ({
        name: day,
        value: count,
      }))
      .sort((a, b) => {
        const dayOrder = [
          "Monday",
          "Tuesday",
          "Wednesday",
          "Thursday",
          "Friday",
          "Saturday",
          "Sunday",
        ];
        return dayOrder.indexOf(a.name) - dayOrder.indexOf(b.name);
      });

    const blockData = Object.entries(timeBlocks)
      .map(([block, count]) => ({
        name: block,
        exams: count,
      }))
      .sort((a, b) => {
        // Extract block number from string like "1 (8:00 AM - 9:30 AM)"
        const getBlockNum = (str: string) => {
          const match = str.match(/^(\d+)/);
          return match ? parseInt(match[1], 10) : 0;
        };
        return getBlockNum(a.name) - getBlockNum(b.name);
      });

    // Calculate schedule efficiency (percentage of exams placed successfully)
    const scheduleEfficiency =
      summary.num_classes > 0
        ? (schedule.total_exams / summary.num_classes) * 100
        : 0;

    return {
      overview: {
        totalExams: schedule.total_exams,
        totalConflicts: summary.real_conflicts,
        roomUtilization: Math.round(roomUtilization * 10) / 10,
        scheduleEfficiency: Math.round(scheduleEfficiency * 10) / 10,
        totalStudents: summary.num_students,
        totalRooms: summary.num_rooms,
        slotsUsed: summary.slots_used,
        backToBackWarnings: conflicts.total,
      },
      dayData,
      blockData,
      conflictBreakdown,
      studentsPerDayData,
    };
  }, [currentSchedule]);

  if (!currentSchedule || !stats) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Statistics Dashboard</CardTitle>
          <CardDescription>
            Generate a schedule to view statistics
          </CardDescription>
        </CardHeader>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {/* Overview Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Exams</CardTitle>
            <BookOpen className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {stats.overview.totalExams}
            </div>
            <p className="text-xs text-muted-foreground">
              {stats.overview.totalStudents} students enrolled
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Conflicts</CardTitle>
            <AlertTriangle className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-destructive">
              {stats.overview.totalConflicts}
            </div>
            <p className="text-xs text-muted-foreground">
              {stats.overview.backToBackWarnings > 0 && (
                <>{stats.overview.backToBackWarnings} back-to-back warnings</>
              )}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              Room Utilization
            </CardTitle>
            <Building2 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {stats.overview.roomUtilization}%
            </div>
            <p className="text-xs text-muted-foreground">
              {stats.overview.totalRooms} rooms available
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              Schedule Efficiency
            </CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {stats.overview.scheduleEfficiency}%
            </div>
            <p className="text-xs text-muted-foreground">
              {stats.overview.slotsUsed} time slots used
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Charts Grid */}
      <div className="grid gap-4 md:grid-cols-2">
        {/* Exams Per Day Bar Chart */}
        <Card>
          <CardHeader>
            <CardTitle>Exams Per Day</CardTitle>
            <CardDescription>
              Distribution of exams across the exam period
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={stats.dayData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis
                  dataKey="name"
                  angle={-45}
                  textAnchor="end"
                  height={80}
                />
                <YAxis />
                <Tooltip />
                <Bar dataKey="exams" fill={COLORS.primary} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Students Per Day Pie Chart */}
        <Card>
          <CardHeader>
            <CardTitle>Students Taking Exams by Day</CardTitle>
            <CardDescription>
              Distribution of student exam instances across days
            </CardDescription>
          </CardHeader>
          <CardContent>
            {stats.studentsPerDayData.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie
                    data={stats.studentsPerDayData}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={({ percent, value, name }) => {
                      // Show percentage and day name for larger segments
                      if (
                        percent > 0.05 ||
                        stats.studentsPerDayData.length === 1
                      ) {
                        return `${name}: ${(percent * 100).toFixed(0)}%`;
                      }
                      return "";
                    }}
                    outerRadius={80}
                    fill="#8884d8"
                    dataKey="value"
                  >
                    {stats.studentsPerDayData.map((entry, index) => (
                      <Cell
                        key={`cell-${index}`}
                        fill={
                          [
                            COLORS.primary,
                            COLORS.success,
                            COLORS.warning,
                            COLORS.info,
                            COLORS.danger,
                            "#8b5cf6",
                            "#ec4899",
                          ][index % 7]
                        }
                      />
                    ))}
                  </Pie>
                  <Tooltip
                    formatter={(value: number, name: string, props: any) => {
                      // Show full name in tooltip
                      const fullName = props.payload?.name || name;
                      return [
                        `${value.toLocaleString()} student${value !== 1 ? "s" : ""}`,
                        fullName,
                      ];
                    }}
                  />
                  <Legend
                    formatter={(value: string) => {
                      return value;
                    }}
                    wrapperStyle={{ paddingTop: "20px" }}
                  />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-[300px] text-muted-foreground">
                No exam data available
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Time Block Distribution */}
      {stats.blockData.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Exams Per Time Block</CardTitle>
            <CardDescription>
              Distribution of exams across different time slots
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={stats.blockData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis
                  dataKey="name"
                  angle={-45}
                  textAnchor="end"
                  height={100}
                />
                <YAxis />
                <Tooltip />
                <Bar dataKey="exams" fill={COLORS.info} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      )}

      {/* Detailed Conflicts Table */}
      {(currentSchedule.conflicts.breakdown.length > 0 ||
        currentSchedule.summary.real_conflicts > 0) && (
        <Card>
          <CardHeader>
            <CardTitle>Detailed Conflict Information</CardTitle>
            <CardDescription>
              Complete list of all conflicts with day, time slot,
              student/instructor, and courses
              {currentSchedule.summary.real_conflicts > 0 &&
                currentSchedule.conflicts.breakdown.filter(
                  (c) => c.conflict_type !== "back_to_back",
                ).length === 0 && (
                  <span className="block mt-2 text-xs text-muted-foreground">
                    Note: {currentSchedule.summary.real_conflicts} conflict(s)
                    detected but detailed information not available. Check
                    backend logs for more details.
                  </span>
                )}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              {currentSchedule.conflicts.breakdown.filter(
                (c) => c.conflict_type !== "back_to_back",
              ).length > 0 ? (
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b">
                      <th className="text-left p-2">Type</th>
                      <th className="text-left p-2">Student/Instructor</th>
                      <th className="text-left p-2">Day</th>
                      <th className="text-left p-2">Time Slot</th>
                      <th className="text-left p-2">Course (CRN)</th>
                      <th className="text-left p-2">Conflicting Course(s)</th>
                    </tr>
                  </thead>
                  <tbody>
                    {currentSchedule.conflicts.breakdown
                      .filter(
                        (conflict) => conflict.conflict_type !== "back_to_back",
                      )
                      .map((conflict, index) => {
                        const entityId =
                          conflict.entity_id ||
                          conflict.student_id ||
                          "Unknown";
                        const conflictTypeName =
                          conflict.conflict_type
                            ?.replace("_", " ")
                            .replace(/\b\w/g, (l) => l.toUpperCase()) ||
                          "Unknown";
                        const day = conflict.day || "Unknown";
                        const blockTime =
                          conflict.block_time ||
                          (conflict.blocks && conflict.blocks.length > 0
                            ? `Blocks: ${conflict.blocks.join(", ")}`
                            : "Unknown");

                        // Extract Course ID and CRN - handle stringified pandas Series
                        let courseId = conflict.course || "Unknown";
                        let crn = conflict.crn || "Unknown";

                        // Clean up courseId if it looks like a pandas Series string
                        if (typeof courseId === "string") {
                          // Remove pandas Series artifacts like "course_ref CS3000 course_ref CS3000"
                          const match = courseId.match(/course_ref\s+(\S+)/);
                          if (match) {
                            courseId = match[1];
                          }
                          // Remove other artifacts
                          courseId = courseId
                            .replace(/Name:\s*\d+,\s*dtype:\s*\w+.*$/, "")
                            .trim();
                        }

                        // Get conflicting courses data - handle both array and single value formats
                        let conflictingCoursesList: string[] = [];
                        let conflictingCrnsList: string[] = [];

                        // Check for array format first
                        if (
                          Array.isArray(conflict.conflicting_courses) &&
                          conflict.conflicting_courses.length > 0
                        ) {
                          conflictingCoursesList = conflict.conflicting_courses;
                        } else if (conflict.conflicting_course) {
                          // Single conflicting course
                          conflictingCoursesList = [
                            conflict.conflicting_course,
                          ];
                        }

                        // Check for array format for CRNs
                        if (
                          Array.isArray(conflict.conflicting_crns) &&
                          conflict.conflicting_crns.length > 0
                        ) {
                          conflictingCrnsList = conflict.conflicting_crns;
                        } else if (conflict.conflicting_crn) {
                          // Single conflicting CRN
                          conflictingCrnsList = [conflict.conflicting_crn];
                        }

                        // Ensure both lists have the same length by padding with empty strings if needed
                        while (
                          conflictingCrnsList.length <
                          conflictingCoursesList.length
                        ) {
                          conflictingCrnsList.push("—");
                        }

                        return (
                          <tr
                            key={index}
                            className="border-b hover:bg-muted/50"
                          >
                            <td className="p-2">
                              <span className="inline-flex items-center px-2 py-1 rounded-md text-xs font-medium bg-destructive/10 text-destructive">
                                {conflictTypeName}
                              </span>
                            </td>
                            <td className="p-2 font-mono text-xs">
                              {entityId}
                            </td>
                            <td className="p-2">{day}</td>
                            <td className="p-2">{blockTime}</td>
                            <td className="p-2">
                              <div className="font-medium">{courseId}</div>
                              <div className="text-xs text-muted-foreground">
                                CRN: {crn}
                              </div>
                            </td>
                            <td className="p-2">
                              {conflictingCoursesList.length > 0 ? (
                                <div className="space-y-1">
                                  {conflictingCoursesList.map(
                                    (confCourse, idx) => {
                                      // Clean up course ID similar to above
                                      let cleanCourseId = confCourse;
                                      if (typeof cleanCourseId === "string") {
                                        // Remove pandas Series artifacts like "course_ref CS3000 course_ref CS3000"
                                        const match =
                                          cleanCourseId.match(
                                            /course_ref\s+(\S+)/,
                                          );
                                        if (match) {
                                          cleanCourseId = match[1];
                                        }
                                        // Remove other artifacts
                                        cleanCourseId = cleanCourseId
                                          .replace(
                                            /Name:\s*\d+,\s*dtype:\s*\w+.*$/,
                                            "",
                                          )
                                          .trim();
                                      }
                                      // Get corresponding CRN, fallback to empty string if not available
                                      const confCrn =
                                        conflictingCrnsList[idx] || "—";
                                      return (
                                        <div
                                          key={idx}
                                          className="text-destructive"
                                        >
                                          <div className="font-medium">
                                            {cleanCourseId || "Unknown"}
                                          </div>
                                          <div className="text-xs text-muted-foreground">
                                            CRN: {confCrn}
                                          </div>
                                        </div>
                                      );
                                    },
                                  )}
                                </div>
                              ) : (
                                <span className="text-muted-foreground">—</span>
                              )}
                            </td>
                          </tr>
                        );
                      })}
                  </tbody>
                </table>
              ) : (
                <div className="text-center py-8">
                  <p className="text-muted-foreground mb-2">
                    No detailed conflict information available
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {currentSchedule.summary.real_conflicts} conflict(s)
                    detected but breakdown data is missing. This may indicate a
                    backend processing issue. Check the backend logs for
                    details.
                  </p>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
