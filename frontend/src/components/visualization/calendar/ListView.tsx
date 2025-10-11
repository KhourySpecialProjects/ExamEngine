"use client";

import {
  type ColumnDef,
  createColumnHelper,
  flexRender,
  getCoreRowModel,
  getSortedRowModel,
  useReactTable,
} from "@tanstack/react-table";
import { AlertCircle } from "lucide-react";
import type { Exam } from "@/store/calendarStore";
import { useCalendarStore } from "@/store/calendarStore";

const columnHelper = createColumnHelper<Exam>();

/**
 * ListView - Table view of all exams with search button
 *
 * Shows all exam details in a sortable table format.
 * Search triggers only when clicking the search button or pressing Enter.
 */
export default function ListView() {
  const allExams = useCalendarStore((state) => state.allExams);
  const filteredExams = useCalendarStore((state) => state.getFilteredExams)();
  const columns: ColumnDef<Exam, any>[] = [
    columnHelper.accessor("courseCode", {
      header: "Course",
      cell: (info) => (
        <div>
          <div className="font-medium">{info.getValue()}</div>
          <div className="text-xs text-gray-500">
            Section {info.row.original.section}
          </div>
        </div>
      ),
    }),
    columnHelper.accessor("day", {
      header: "Day",
      cell: (info) => <div className="text-sm">{info.getValue()}</div>,
    }),
    columnHelper.accessor("timeSlot", {
      header: "Time",
      cell: (info) => <div className="text-sm">{info.getValue()}</div>,
    }),
    columnHelper.accessor("room", {
      header: "Room",
      cell: (info) => <div className="text-sm">{info.getValue()}</div>,
    }),
    columnHelper.accessor("instructor", {
      header: "Instructor",
      cell: (info) => <div className="text-sm">{info.getValue()}</div>,
    }),
    columnHelper.accessor("studentCount", {
      header: "Students",
      cell: (info) => (
        <div className="text-sm text-right">{info.getValue()}</div>
      ),
    }),
    columnHelper.accessor("conflicts", {
      header: "Conflicts",
      cell: (info) => (
        <div className="text-center">
          {info.getValue() > 0 ? (
            <span className="inline-flex items-center gap-1 bg-red-100 text-red-700 text-xs px-2 py-0.5 rounded-full">
              <AlertCircle className="size-3" />
              {info.getValue()}
            </span>
          ) : (
            <span className="text-gray-400">—</span>
          )}
        </div>
      ),
    }),
  ];

  const table = useReactTable({
    data: filteredExams,
    columns,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  });

  return (
    <div className="space-y-4">
      {/* Data Table */}
      <div className="bg-white rounded-lg shadow-lg overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-100 border-b-2 border-gray-300">
              {table.getHeaderGroups().map((headerGroup) => (
                <tr key={headerGroup.id}>
                  {headerGroup.headers.map((header) => (
                    <th
                      key={header.id}
                      className="px-4 py-3 text-left text-sm font-semibold"
                    >
                      {flexRender(
                        header.column.columnDef.header,
                        header.getContext(),
                      )}
                    </th>
                  ))}
                </tr>
              ))}
            </thead>
            <tbody className="divide-y">
              {table.getRowModel().rows.length === 0 ? (
                <tr>
                  <td
                    colSpan={columns.length}
                    className="px-4 py-12 text-center text-gray-500"
                  >
                    <div className="flex flex-col items-center gap-2">
                      <AlertCircle className="size-12 opacity-20" />
                      <p>No exams found</p>
                      {allExams.length === 0 ? (
                        <p className="text-sm">No data loaded yet</p>
                      ) : (
                        <p className="text-sm">
                          Try adjusting your search or filters
                        </p>
                      )}
                      <p className="text-xs text-gray-400 mt-2">
                        Total: {allExams.length} | Filtered:{" "}
                        {filteredExams.length}
                      </p>
                    </div>
                  </td>
                </tr>
              ) : (
                table.getRowModel().rows.map((row) => (
                  <tr
                    key={row.id}
                    className="hover:bg-gray-50 transition-colors"
                  >
                    {row.getVisibleCells().map((cell) => (
                      <td key={cell.id} className="px-4 py-3">
                        {flexRender(
                          cell.column.columnDef.cell,
                          cell.getContext(),
                        )}
                      </td>
                    ))}
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
