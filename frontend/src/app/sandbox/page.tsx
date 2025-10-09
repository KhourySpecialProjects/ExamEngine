"use client";
import { useState } from "react";
import {
  X,
  AlertCircle,
  Users,
  Building2,
  Clock,
  Search,
  Filter,
  Download,
  List,
  Grid3x3,
  BarChart3,
  Calendar,
  ChevronRight,
  SlidersHorizontal,
} from "lucide-react";

// Sample data generator
const generateSampleData = () => {
  const days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"];
  const timeSlots = [
    "8:00 - 10:00 AM",
    "10:00 AM - 12:00 PM",
    "12:00 - 2:00 PM",
    "2:00 - 4:00 PM",
    "4:00 - 6:00 PM",
  ];

  const departments = ["CS", "MATH", "PHYS", "CHEM", "EECE", "BUSN"];
  const buildings = ["WVH", "Shillman", "Kariotis", "Ryder", "Churchill"];

  const data = [];

  timeSlots.forEach((timeSlot) => {
    const row = { timeSlot, days: [] };

    days.forEach((day) => {
      const examCount = Math.floor(Math.random() * 31);
      const conflicts = examCount > 15 ? Math.floor(Math.random() * 5) : 0;

      const exams = [];
      for (let i = 0; i < examCount; i++) {
        const dept =
          departments[Math.floor(Math.random() * departments.length)];
        const building =
          buildings[Math.floor(Math.random() * buildings.length)];
        exams.push({
          id: `exam-${day}-${timeSlot}-${i}`,
          courseCode: `${dept} ${1000 + Math.floor(Math.random() * 4000)}`,
          section: `0${Math.floor(Math.random() * 5) + 1}`,
          department: dept,
          instructor: [
            "Dr. Smith",
            "Prof. Johnson",
            "Dr. Williams",
            "Prof. Davis",
          ][Math.floor(Math.random() * 4)],
          studentCount: 50 + Math.floor(Math.random() * 150),
          room: `${building} ${100 + Math.floor(Math.random() * 300)}`,
          building: building,
          conflicts: i < conflicts ? Math.floor(Math.random() * 3) + 1 : 0,
          day,
          timeSlot,
        });
      }

      row.days.push({ day, examCount, conflicts, exams });
    });

    data.push(row);
  });

  return data;
};

export default function HybridCalendar() {
  const [scheduleData] = useState(generateSampleData());
  const [viewMode, setViewMode] = useState("heatmap"); // heatmap, compact, list
  const [selectedCell, setSelectedCell] = useState(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [departmentFilter, setDepartmentFilter] = useState("");
  const [showConflictsOnly, setShowConflictsOnly] = useState(false);
  const [showFilters, setShowFilters] = useState(false);

  // Get all exams as flat array
  const allExams = scheduleData.flatMap((row) =>
    row.days.flatMap((day) => day.exams),
  );

  // Filter exams
  const filteredExams = allExams.filter((exam) => {
    if (
      searchQuery &&
      !exam.courseCode.toLowerCase().includes(searchQuery.toLowerCase()) &&
      !exam.instructor.toLowerCase().includes(searchQuery.toLowerCase()) &&
      !exam.room.toLowerCase().includes(searchQuery.toLowerCase())
    ) {
      return false;
    }
    if (departmentFilter && exam.department !== departmentFilter) {
      return false;
    }
    if (showConflictsOnly && exam.conflicts === 0) {
      return false;
    }
    return true;
  });

  // Get unique departments
  const departments = [...new Set(allExams.map((e) => e.department))].sort();

  // Calculate stats
  const totalExams = allExams.length;
  const totalConflicts = allExams.reduce(
    (sum, exam) => sum + exam.conflicts,
    0,
  );
  const busiestSlot = Math.max(
    ...scheduleData.flatMap((row) => row.days.map((d) => d.examCount)),
  );

  // Color coding
  const getDensityColor = (count) => {
    if (count === 0) return "bg-gray-50 text-gray-400 border-gray-200";
    if (count <= 5) return "bg-green-100 text-green-900 border-green-300";
    if (count <= 10) return "bg-yellow-100 text-yellow-900 border-yellow-300";
    if (count <= 20) return "bg-orange-200 text-orange-900 border-orange-400";
    return "bg-red-300 text-red-900 border-red-500";
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b shadow-sm">
        <div className="max-w-[1600px] mx-auto px-6 py-4">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h1 className="text-3xl font-bold flex items-center gap-2">
                <Calendar className="size-8 text-blue-600" />
                ExamEngine Schedule
              </h1>
              <p className="text-gray-600 text-sm mt-1">
                Fall 2025 Final Exam Schedule
              </p>
            </div>
            <button className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center gap-2">
              <Download className="size-4" />
              Export
            </button>
          </div>

          {/* Stats Row */}
          <div className="grid grid-cols-4 gap-4 mb-4">
            <div className="bg-blue-50 rounded-lg p-3 border border-blue-200">
              <div className="flex items-center gap-2 text-blue-600 text-xs mb-1">
                <Calendar className="size-3" />
                Total Exams
              </div>
              <div className="text-2xl font-bold text-blue-900">
                {viewMode === "list" ? filteredExams.length : totalExams}
              </div>
              {viewMode === "list" && filteredExams.length < totalExams && (
                <div className="text-xs text-blue-600 mt-1">
                  Filtered from {totalExams}
                </div>
              )}
            </div>
            <div className="bg-orange-50 rounded-lg p-3 border border-orange-200">
              <div className="flex items-center gap-2 text-orange-600 text-xs mb-1">
                <BarChart3 className="size-3" />
                Busiest Slot
              </div>
              <div className="text-2xl font-bold text-orange-900">
                {busiestSlot}
              </div>
              <div className="text-xs text-orange-600">exams in one slot</div>
            </div>
            <div className="bg-red-50 rounded-lg p-3 border border-red-200">
              <div className="flex items-center gap-2 text-red-600 text-xs mb-1">
                <AlertCircle className="size-3" />
                Total Conflicts
              </div>
              <div className="text-2xl font-bold text-red-900">
                {totalConflicts}
              </div>
            </div>
            <div className="bg-purple-50 rounded-lg p-3 border border-purple-200">
              <div className="flex items-center gap-2 text-purple-600 text-xs mb-1">
                <Building2 className="size-3" />
                Rooms Used
              </div>
              <div className="text-2xl font-bold text-purple-900">
                {new Set(allExams.map((e) => e.room)).size}
              </div>
            </div>
          </div>

          {/* Controls Row */}
          <div className="flex gap-2 items-center">
            {/* Search */}
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-gray-400" />
              <input
                type="text"
                placeholder="Search courses, instructors, rooms..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>

            {/* Filters Toggle */}
            <button
              onClick={() => setShowFilters(!showFilters)}
              className={`px-4 py-2 border rounded-lg flex items-center gap-2 transition-colors ${
                showFilters
                  ? "bg-blue-50 border-blue-300 text-blue-700"
                  : "hover:bg-gray-50"
              }`}
            >
              <SlidersHorizontal className="size-4" />
              Filters
              {(departmentFilter || showConflictsOnly) && (
                <span className="bg-blue-600 text-white text-xs px-1.5 py-0.5 rounded-full">
                  {(departmentFilter ? 1 : 0) + (showConflictsOnly ? 1 : 0)}
                </span>
              )}
            </button>

            {/* View Mode Switcher */}
            <div className="flex gap-1 border rounded-lg p-1 bg-gray-100">
              <button
                onClick={() => setViewMode("heatmap")}
                className={`px-3 py-2 rounded flex items-center gap-2 transition-colors ${
                  viewMode === "heatmap"
                    ? "bg-white shadow-sm"
                    : "hover:bg-gray-50"
                }`}
                title="Heatmap View"
              >
                <Grid3x3 className="size-4" />
                <span className="text-sm font-medium">Heatmap</span>
              </button>
              <button
                onClick={() => setViewMode("compact")}
                className={`px-3 py-2 rounded flex items-center gap-2 transition-colors ${
                  viewMode === "compact"
                    ? "bg-white shadow-sm"
                    : "hover:bg-gray-50"
                }`}
                title="Compact View"
              >
                <Calendar className="size-4" />
                <span className="text-sm font-medium">Compact</span>
              </button>
              <button
                onClick={() => setViewMode("list")}
                className={`px-3 py-2 rounded flex items-center gap-2 transition-colors ${
                  viewMode === "list"
                    ? "bg-white shadow-sm"
                    : "hover:bg-gray-50"
                }`}
                title="List View"
              >
                <List className="size-4" />
                <span className="text-sm font-medium">List</span>
              </button>
            </div>
          </div>

          {/* Expandable Filters */}
          {showFilters && (
            <div className="mt-4 p-4 bg-gray-50 rounded-lg border flex gap-4">
              <select
                value={departmentFilter}
                onChange={(e) => setDepartmentFilter(e.target.value)}
                className="px-3 py-2 border rounded-lg bg-white"
              >
                <option value="">All Departments</option>
                {departments.map((dept) => (
                  <option key={dept} value={dept}>
                    {dept}
                  </option>
                ))}
              </select>

              <label className="flex items-center gap-2 px-3 py-2 border rounded-lg bg-white cursor-pointer">
                <input
                  type="checkbox"
                  checked={showConflictsOnly}
                  onChange={(e) => setShowConflictsOnly(e.target.checked)}
                  className="w-4 h-4"
                />
                <span className="text-sm">Show conflicts only</span>
              </label>

              {(departmentFilter || showConflictsOnly) && (
                <button
                  onClick={() => {
                    setDepartmentFilter("");
                    setShowConflictsOnly(false);
                  }}
                  className="px-3 py-2 text-sm text-gray-600 hover:text-gray-900"
                >
                  Clear filters
                </button>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-[1600px] mx-auto px-6 py-6">
        {/* HEATMAP VIEW */}
        {viewMode === "heatmap" && (
          <div className="space-y-4">
            <div className="bg-white rounded-lg shadow-lg overflow-hidden">
              <table className="w-full border-collapse">
                <thead>
                  <tr className="bg-gray-100 border-b-2 border-gray-300">
                    <th className="border border-gray-300 p-4 text-left font-semibold w-40">
                      Time Slot
                    </th>
                    {[
                      "Monday",
                      "Tuesday",
                      "Wednesday",
                      "Thursday",
                      "Friday",
                    ].map((day) => (
                      <th
                        key={day}
                        className="border border-gray-300 p-4 text-center font-semibold"
                      >
                        {day}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {scheduleData.map((row, rowIdx) => (
                    <tr key={rowIdx}>
                      <td className="border border-gray-300 p-4 bg-gray-50 font-medium text-sm">
                        {row.timeSlot}
                      </td>
                      {row.days.map((cell, cellIdx) => {
                        const colorClass = getDensityColor(cell.examCount);

                        return (
                          <td
                            key={cellIdx}
                            className="border border-gray-300 p-0"
                          >
                            <div
                              onClick={() =>
                                cell.examCount > 0 &&
                                setSelectedCell({
                                  ...cell,
                                  timeSlot: row.timeSlot,
                                })
                              }
                              className={`
                                ${colorClass} border-2
                                min-h-[120px] p-4 cursor-pointer 
                                transition-all duration-200
                                ${cell.examCount > 0 ? "hover:scale-105 hover:shadow-lg hover:z-10 relative" : ""}
                              `}
                            >
                              <div className="flex flex-col items-center justify-center h-full">
                                <div className="text-4xl font-bold mb-1">
                                  {cell.examCount}
                                </div>
                                <div className="text-xs font-medium mb-2">
                                  {cell.examCount === 1 ? "exam" : "exams"}
                                </div>
                                {cell.conflicts > 0 && (
                                  <div className="flex items-center gap-1 text-xs bg-red-500 text-white px-2 py-0.5 rounded-full">
                                    <AlertCircle className="size-3" />
                                    {cell.conflicts}
                                  </div>
                                )}
                              </div>
                            </div>
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Legend */}
            <div className="bg-white rounded-lg shadow p-4">
              <h3 className="font-semibold mb-3 text-sm">Density Legend</h3>
              <div className="flex gap-3 items-center flex-wrap text-sm">
                <div className="flex items-center gap-2">
                  <div className="w-10 h-10 bg-gray-50 border-2 border-gray-200 rounded"></div>
                  <span>Empty</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-10 h-10 bg-green-100 border-2 border-green-300 rounded"></div>
                  <span>1-5</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-10 h-10 bg-yellow-100 border-2 border-yellow-300 rounded"></div>
                  <span>6-10</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-10 h-10 bg-orange-200 border-2 border-orange-400 rounded"></div>
                  <span>11-20</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-10 h-10 bg-red-300 border-2 border-red-500 rounded"></div>
                  <span>20+</span>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* COMPACT VIEW */}
        {viewMode === "compact" && (
          <div className="bg-white rounded-lg shadow-lg overflow-hidden">
            <table className="w-full border-collapse">
              <thead>
                <tr className="bg-gray-100 border-b-2 border-gray-300">
                  <th className="border border-gray-300 p-3 text-left font-semibold w-40">
                    Time Slot
                  </th>
                  {["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"].map(
                    (day) => (
                      <th
                        key={day}
                        className="border border-gray-300 p-3 text-center font-semibold"
                      >
                        {day}
                      </th>
                    ),
                  )}
                </tr>
              </thead>
              <tbody>
                {scheduleData.map((row, rowIdx) => (
                  <tr key={rowIdx}>
                    <td className="border border-gray-300 p-3 bg-gray-50 font-medium text-sm">
                      {row.timeSlot}
                    </td>
                    {row.days.map((cell, cellIdx) => (
                      <td
                        key={cellIdx}
                        className="border border-gray-300 p-2 align-top"
                      >
                        <div className="space-y-1 max-h-[150px] overflow-y-auto">
                          {cell.exams.slice(0, 6).map((exam) => (
                            <div
                              key={exam.id}
                              onClick={() =>
                                setSelectedCell({
                                  ...cell,
                                  timeSlot: row.timeSlot,
                                })
                              }
                              className="bg-blue-50 border border-blue-200 rounded px-2 py-1 text-xs cursor-pointer hover:bg-blue-100 transition-colors"
                            >
                              <div className="font-medium text-blue-900">
                                {exam.courseCode}
                              </div>
                              <div className="text-gray-600">
                                {exam.studentCount} students
                              </div>
                            </div>
                          ))}
                          {cell.exams.length > 6 && (
                            <button
                              onClick={() =>
                                setSelectedCell({
                                  ...cell,
                                  timeSlot: row.timeSlot,
                                })
                              }
                              className="text-xs text-blue-600 hover:text-blue-800 w-full text-left pl-2"
                            >
                              +{cell.exams.length - 6} more
                            </button>
                          )}
                        </div>
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* LIST VIEW */}
        {viewMode === "list" && (
          <div className="bg-white rounded-lg shadow-lg overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-100 border-b-2 border-gray-300">
                  <tr>
                    <th className="px-4 py-3 text-left text-sm font-semibold">
                      Course
                    </th>
                    <th className="px-4 py-3 text-left text-sm font-semibold">
                      Day
                    </th>
                    <th className="px-4 py-3 text-left text-sm font-semibold">
                      Time
                    </th>
                    <th className="px-4 py-3 text-left text-sm font-semibold">
                      Room
                    </th>
                    <th className="px-4 py-3 text-left text-sm font-semibold">
                      Instructor
                    </th>
                    <th className="px-4 py-3 text-right text-sm font-semibold">
                      Students
                    </th>
                    <th className="px-4 py-3 text-center text-sm font-semibold">
                      Conflicts
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {filteredExams.map((exam) => (
                    <tr key={exam.id} className="hover:bg-gray-50">
                      <td className="px-4 py-3">
                        <div className="font-medium">{exam.courseCode}</div>
                        <div className="text-xs text-gray-500">
                          Section {exam.section}
                        </div>
                      </td>
                      <td className="px-4 py-3 text-sm">{exam.day}</td>
                      <td className="px-4 py-3 text-sm">{exam.timeSlot}</td>
                      <td className="px-4 py-3 text-sm">{exam.room}</td>
                      <td className="px-4 py-3 text-sm">{exam.instructor}</td>
                      <td className="px-4 py-3 text-sm text-right">
                        {exam.studentCount}
                      </td>
                      <td className="px-4 py-3 text-center">
                        {exam.conflicts > 0 ? (
                          <span className="inline-flex items-center gap-1 bg-red-100 text-red-700 text-xs px-2 py-0.5 rounded-full">
                            <AlertCircle className="size-3" />
                            {exam.conflicts}
                          </span>
                        ) : (
                          <span className="text-gray-400">—</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>

      {/* Detail Modal */}
      {selectedCell && (
        <div
          className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
          onClick={() => setSelectedCell(null)}
        >
          <div
            className="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] flex flex-col"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-start justify-between p-6 border-b">
              <div>
                <h2 className="text-2xl font-bold mb-1">{selectedCell.day}</h2>
                <div className="flex items-center gap-2 text-gray-600">
                  <Clock className="size-4" />
                  <span className="text-sm">{selectedCell.timeSlot}</span>
                </div>
              </div>
              <button
                onClick={() => setSelectedCell(null)}
                className="p-2 hover:bg-gray-100 rounded-lg"
              >
                <X className="size-5" />
              </button>
            </div>

            <div className="grid grid-cols-3 gap-4 p-6 border-b bg-gray-50">
              <div>
                <div className="text-xs text-gray-600 mb-1">Total Exams</div>
                <div className="text-3xl font-bold">
                  {selectedCell.examCount}
                </div>
              </div>
              <div>
                <div className="text-xs text-gray-600 mb-1">Total Students</div>
                <div className="text-3xl font-bold">
                  {selectedCell.exams.reduce(
                    (sum, exam) => sum + exam.studentCount,
                    0,
                  )}
                </div>
              </div>
              <div>
                <div className="text-xs text-gray-600 mb-1">Conflicts</div>
                <div className="text-3xl font-bold text-red-600">
                  {selectedCell.conflicts}
                </div>
              </div>
            </div>

            <div className="flex-1 overflow-y-auto p-6">
              <div className="space-y-3">
                {selectedCell.exams.map((exam) => (
                  <div
                    key={exam.id}
                    className="border rounded-lg p-4 hover:bg-gray-50"
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-2">
                          <span className="font-semibold text-lg">
                            {exam.courseCode} - Section {exam.section}
                          </span>
                          {exam.conflicts > 0 && (
                            <span className="bg-red-100 text-red-700 text-xs px-2 py-0.5 rounded-full flex items-center gap-1">
                              <AlertCircle className="size-3" />
                              {exam.conflicts} conflicts
                            </span>
                          )}
                        </div>
                        <div className="flex gap-4 text-sm text-gray-600">
                          <div className="flex items-center gap-1">
                            <Users className="size-4" />
                            {exam.studentCount} students
                          </div>
                          <div className="flex items-center gap-1">
                            <Building2 className="size-4" />
                            {exam.room}
                          </div>
                          <div>{exam.instructor}</div>
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
