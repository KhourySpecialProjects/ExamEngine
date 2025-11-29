"use client";

import { useMemo } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useSchedulesStore } from "@/lib/store/schedulesStore";
import { useDatasetStore } from "@/lib/store/datasetStore";
import { BookOpen, AlertTriangle, Building2, TrendingUp } from "lucide-react";

const COLORS = {
  primary: "#3b82f6",
  success: "#10b981",
  warning: "#f59e0b",
  danger: "#ef4444",
  info: "#6366f1",
};

interface ConflictData {
  name: string;
  value: number;
}

export function StatisticsView() {
  const currentSchedule = useSchedulesStore((state) => state.currentSchedule);
  const datasets = useDatasetStore((state) => state.datasets);
  
  const stats = useMemo(() => {
    if (!currentSchedule) return null;

    const schedule = currentSchedule.schedule;
    const summary = currentSchedule.summary;
    const conflicts = currentSchedule.conflicts;
    
    // Try to get unique student count from dataset if available
    const dataset = datasets.find((d) => d.dataset_id === currentSchedule.dataset_id);
    const uniqueStudents = dataset?.files?.enrollments?.unique_students || null;

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

    if (Object.keys(conflictTypes).length === 0 && summary.real_conflicts > 0) {
      conflictTypes["unknown"] = summary.real_conflicts;
      // Debug: log this issue (safely handle missing breakdown)
      const breakdownCount = Array.isArray(conflicts?.breakdown)
        ? conflicts.breakdown.length
        : 0;
      console.warn(
        `Conflict mismatch: ${summary.real_conflicts} conflicts reported but ${breakdownCount} items in breakdown.`,
        "Breakdown items:",
        conflicts?.breakdown,
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

    // Calculate unique students
    // Note: summary.num_students is the sum of all enrollments (not unique students)
    // Try to get the actual unique student count from the dataset
    // If not available, fall back to summary.num_students (which is sum of enrollments)
    const totalUniqueStudents = uniqueStudents || summary.num_students || 0;

    // Calculate back-to-back warnings from metrics
    const breakdown = conflicts.breakdown || [];
    const studentsBackToBack = breakdown.filter(
      (c: any) => c.conflict_type === "back_to_back" || c.conflict_type === "back_to_back_student"
    ).length;
    const instructorsBackToBack = breakdown.filter(
      (c: any) => c.conflict_type === "back_to_back_instructor"
    ).length;
    const totalBackToBackWarnings = studentsBackToBack + instructorsBackToBack;

    return {
      overview: {
        totalExams: schedule.total_exams,
        totalConflicts: summary.real_conflicts,
        roomUtilization: Math.round(roomUtilization * 10) / 10,
        scheduleEfficiency: Math.round(scheduleEfficiency * 10) / 10,
        totalStudents: totalUniqueStudents,
        totalRooms: summary.num_rooms,
        slotsUsed: summary.slots_used,
        backToBackWarnings: totalBackToBackWarnings,
      },
      dayData,
      blockData,
      conflictBreakdown,
      studentsPerDayData,
    };
  }, [currentSchedule, datasets]);

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
      <div className="flex items-center justify-between gap-2">
        <div className="pl-2">
          <h1 className="text-2xl font-bold">Statistics View</h1>
          <p className="text-muted-foreground">
            Analytics and insights about your exam schedule
          </p>
        </div>
      </div>
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
                    label={({ percent, name }) => {
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
                    {stats.studentsPerDayData.map((_entry, index) => (
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
    </div>
  );
}
