import {
  type ColumnDef,
  createColumnHelper,
  flexRender,
  getCoreRowModel,
  useReactTable,
} from "@tanstack/react-table";
import { type ReactNode, useMemo } from "react";
import type { CalendarRow, Exam } from "@/lib/types/calendar.types";

interface CalendarGridProps {
  /**
   * Calendar data organized by rows (time slots)
   */
  data: CalendarRow[];

  /**
   * Array of day labels (e.g., ['Monday', 'Tuesday', ...])
   */
  days: string[];

  /**
   * Function to render each cell's content
   */
  renderCell: (cell: {
    day: string;
    timeSlot: string;
    examCount: number;
    conflicts: number;
    exams: Exam[];
  }) => ReactNode;

  /**
   * Optional: Custom className for the container
   */
  className?: string;

  /**
   * Optional: Show row labels (time slots)
   */
  showTimeSlots?: boolean;

  /**
   * Optional: Minimum cell height
   */
  minCellHeight?: string;

  /**
   * Optional: Minimum cell width
   */
  minCellWidth?: number;

  /**
   * Optional: Default cell width
   */
  defaultCellWidth?: number;

  /**
   * Optional: Time slot column width
   */
  timeSlotWidth?: number;
}

/**
 * CalendarGrid - Reusable calendar grid component
 *
 * This component provides the grid structure for calendar views.
 * It handles the layout and passes cell data to the renderCell function.
 */
export function CalendarGrid({
  data,
  days,
  renderCell,
  className = "",
  showTimeSlots = true,
  minCellHeight = "min-h-[120px]",
  minCellWidth = 120,
  defaultCellWidth = 120,
  timeSlotWidth = 120,
}: CalendarGridProps) {
  const columnHelper = useMemo(() => createColumnHelper<CalendarRow>(), []);
  const columns = useMemo<ColumnDef<CalendarRow, unknown>[]>(() => {
    const timeSlotColumn = showTimeSlots
      ? columnHelper.display({
          id: "timeSlot",
          header: () => <div className="font-semibold text-sm">Time Slot</div>,
          cell: ({ row }) => (
            <div className="font-medium text-sm">{row.original.timeSlot}</div>
          ),
          size: timeSlotWidth,
          minSize: timeSlotWidth,
          maxSize: timeSlotWidth,
        })
      : null;
    const dayColumns = days.map((day, dayIndex) =>
      columnHelper.display({
        id: day,
        header: () => (
          <div className="font-semibold text-sm text-center">{day}</div>
        ),
        cell: ({ row }) => {
          const cell = row.original.days[dayIndex];
          return (
            <div
              className={minCellHeight}
              style={{ minWidth: `${minCellWidth}px` }}
            >
              {renderCell(cell)}
            </div>
          );
        },
        size: defaultCellWidth,
        minSize: minCellWidth,
      }),
    );
    return timeSlotColumn ? [timeSlotColumn, ...dayColumns] : dayColumns;
  }, [
    days,
    showTimeSlots,
    minCellHeight,
    minCellWidth,
    defaultCellWidth,
    timeSlotWidth,
    renderCell,
    columnHelper,
  ]);

  const table = useReactTable({
    data,
    columns,
    getCoreRowModel: getCoreRowModel(),
    columnResizeMode: "onChange",
  });
  return (
    <div
      className={`bg-white rounded-md shadow-xs overflow-hidden ${className}`}
    >
      <div className="overflow-x-auto overflow-hidden">
        <div className="inline-block min-w-full align-middle">
          <table className="min-w-full border-collapse">
            <thead>
              {table.getHeaderGroups().map((headerGroup) => (
                <tr
                  key={headerGroup.id}
                  className="bg-gray-100 border-b-2 border-gray-300"
                >
                  {headerGroup.headers.map((header) => (
                    <th
                      key={header.id}
                      className="border border-gray-300 p-4 relative"
                      style={{
                        width: header.getSize(),
                        minWidth: header.column.columnDef.minSize,
                      }}
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

            <tbody>
              {table.getRowModel().rows.map((row) => (
                <tr key={row.id}>
                  {row.getVisibleCells().map((cell) => (
                    <td
                      key={cell.id}
                      className="border border-gray-300 p-0 align-middle text-center bg-background"
                      style={{
                        width: cell.column.getSize(),
                        minWidth: cell.column.columnDef.minSize,
                      }}
                    >
                      {flexRender(
                        cell.column.columnDef.cell,
                        cell.getContext(),
                      )}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
