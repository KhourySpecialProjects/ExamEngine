"use client";

import {
  flexRender,
  getCoreRowModel,
  useReactTable,
} from "@tanstack/react-table";
import { AlertCircle, ChevronRight, Database, Search, X } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { DataTableBody } from "@/components/common/table/DataTableBody";
import { PaginationBar } from "@/components/common/table/PaginationBar";
import { createScheduleColumns } from "@/components/schedules/columns";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Table, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import type { ScheduleListItem } from "@/lib/api/schedules";
import {
  GROUP_SORT_LABELS,
  type GroupSort,
  groupSchedulesByDataset,
  SCHEDULE_SORT_LABELS,
  type ScheduleGroup,
  type ScheduleSort,
} from "@/lib/scheduleGroups";
import { useSchedulesViewStore } from "@/lib/store/schedulesViewStore";
import { cn } from "@/lib/utils";

const dateFormat = new Intl.DateTimeFormat("en-US", {
  month: "short",
  day: "numeric",
  year: "numeric",
});
const dateTimeFormat = new Intl.DateTimeFormat("en-US", {
  month: "short",
  day: "numeric",
  year: "numeric",
  hour: "numeric",
  minute: "2-digit",
});

/** "120 courses · 3,400 students · 18 rooms", skipping unknown counts. */
function datasetSize(group: ScheduleGroup): string {
  const { courses, students, rooms } = group.dataset;
  return [
    [courses, "courses"],
    [students, "students"],
    [rooms, "rooms"],
  ]
    .filter(([count]) => count !== null)
    .map(([count, noun]) => `${count?.toLocaleString()} ${noun}`)
    .join(" · ");
}

function SortSelect<T extends string>({
  label,
  value,
  labels,
  onChange,
}: {
  label: string;
  value: T;
  labels: Record<T, string>;
  onChange: (value: T) => void;
}) {
  return (
    <div className="flex items-center gap-2">
      <span className="text-sm text-muted-foreground">{label}</span>
      <Select value={value} onValueChange={(v) => onChange(v as T)}>
        <SelectTrigger size="sm" aria-label={`Sort ${label.toLowerCase()}`}>
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {(Object.keys(labels) as T[]).map((key) => (
            <SelectItem key={key} value={key}>
              {labels[key]}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}

/** One dataset's schedules, already in the chosen order. */
function GroupTable({
  schedules,
  onDelete,
}: {
  schedules: ScheduleListItem[];
  onDelete?: (scheduleId: string) => void;
}) {
  const columns = useMemo(
    () => createScheduleColumns(onDelete, { showDataset: false }),
    [onDelete],
  );
  const table = useReactTable({
    data: schedules,
    columns,
    getCoreRowModel: getCoreRowModel(),
    // Order comes from the view's sort controls.
    enableSorting: false,
  });
  return (
    // Same fixed widths in every group, so columns line up across datasets.
    <Table className="min-w-[880px] table-fixed">
      <TableHeader className="bg-muted/60">
        {table.getHeaderGroups().map((headerGroup) => (
          <TableRow key={headerGroup.id}>
            {headerGroup.headers.map((header) => (
              <TableHead
                key={header.id}
                className={cn(
                  "h-9 text-xs font-semibold uppercase tracking-wide text-muted-foreground",
                  header.column.columnDef.meta?.width,
                )}
              >
                {flexRender(
                  header.column.columnDef.header,
                  header.getContext(),
                )}
              </TableHead>
            ))}
          </TableRow>
        ))}
      </TableHeader>
      <DataTableBody
        table={table}
        columnCount={columns.length}
        cellClassName="whitespace-normal break-words"
      />
    </Table>
  );
}

function DatasetGroup({
  group,
  open,
  onToggle,
  onDelete,
}: {
  group: ScheduleGroup;
  open: boolean;
  onToggle: () => void;
  onDelete?: (scheduleId: string) => void;
}) {
  const count = group.schedules.length;
  const size = datasetSize(group);
  return (
    <section
      aria-label={group.dataset.name || "Unknown dataset"}
      className="overflow-hidden rounded-xl border bg-card shadow-sm"
    >
      <button
        type="button"
        aria-expanded={open}
        onClick={onToggle}
        className="flex w-full items-center gap-3 px-4 py-3 text-left hover:bg-muted/50"
      >
        <ChevronRight
          className={cn(
            "h-4 w-4 shrink-0 text-muted-foreground transition-transform",
            open && "rotate-90",
          )}
        />
        <Database className="h-4 w-4 shrink-0 text-muted-foreground" />
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-semibold">
              {group.dataset.name || "Unknown dataset"}
            </span>
            {group.dataset.deleted && (
              <Badge variant="destructive">Deleted</Badge>
            )}
          </div>
          <div className="text-xs text-muted-foreground">
            {group.dataset.uploaded_at &&
              `Uploaded ${dateFormat.format(new Date(group.dataset.uploaded_at))}`}
            {size && ` · ${size}`}
          </div>
        </div>
        <div className="shrink-0 text-right">
          <div className="text-sm font-medium">
            {count} {count === 1 ? "schedule" : "schedules"}
          </div>
          <div className="text-xs text-muted-foreground">
            Latest run {dateTimeFormat.format(new Date(group.latestRun))}
          </div>
        </div>
      </button>
      {open && (
        <div className="border-t pl-10 pr-2">
          <GroupTable schedules={group.schedules} onDelete={onDelete} />
        </div>
      )}
    </section>
  );
}

interface ScheduleGroupsViewProps {
  schedules: ScheduleListItem[];
  onDelete?: (scheduleId: string) => void;
}

/** Schedules grouped under collapsible dataset cards, paged by dataset. */
export function ScheduleGroupsView({
  schedules,
  onDelete,
}: ScheduleGroupsViewProps) {
  const [search, setSearch] = useState("");
  const [groupSort, setGroupSort] = useState<GroupSort>("latest");
  const [scheduleSort, setScheduleSort] = useState<ScheduleSort>("newest");
  const [page, setPage] = useState(0);
  const pageSize = useSchedulesViewStore((s) => s.datasetPageSize);
  const setPageSize = useSchedulesViewStore((s) => s.setDatasetPageSize);

  const groups = useMemo(
    () =>
      groupSchedulesByDataset(schedules, { search, groupSort, scheduleSort }),
    [schedules, search, groupSort, scheduleSort],
  );

  // Only the dataset with the most recent run starts expanded.
  const [expanded, setExpanded] = useState<ReadonlySet<string>>(() => {
    const [latest] = groupSchedulesByDataset(schedules, {});
    return new Set(latest ? [latest.datasetId] : []);
  });
  const toggle = (datasetId: string) =>
    setExpanded((current) => {
      const next = new Set(current);
      if (!next.delete(datasetId)) next.add(datasetId);
      return next;
    });

  // A narrower search or a deleted schedule can leave the page past the end.
  const pageCount = Math.max(1, Math.ceil(groups.length / pageSize));
  useEffect(() => {
    if (page >= pageCount) setPage(pageCount - 1);
  }, [page, pageCount]);

  const visible = groups.slice(page * pageSize, (page + 1) * pageSize);

  const bar = {
    page,
    pageSize,
    total: groups.length,
    noun: " datasets",
    onPage: setPage,
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-4">
        <div className="relative max-w-sm flex-1">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search schedules or datasets..."
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(0);
            }}
            className="bg-white pl-10 pr-9"
          />
          {search && (
            <Button
              variant="ghost"
              size="sm"
              aria-label="Clear search"
              className="absolute right-1 top-1/2 h-7 w-7 -translate-y-1/2 p-0"
              onClick={() => {
                setSearch("");
                setPage(0);
              }}
            >
              <X className="h-4 w-4" />
            </Button>
          )}
        </div>
        <SortSelect
          label="Datasets"
          value={groupSort}
          labels={GROUP_SORT_LABELS}
          onChange={(value) => {
            setGroupSort(value);
            setPage(0);
          }}
        />
        <SortSelect
          label="Schedules"
          value={scheduleSort}
          labels={SCHEDULE_SORT_LABELS}
          onChange={setScheduleSort}
        />
        <div className="ml-auto flex gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setExpanded(new Set(groups.map((g) => g.datasetId)))}
          >
            Expand all
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setExpanded(new Set())}
          >
            Collapse all
          </Button>
        </div>
      </div>

      <PaginationBar
        {...bar}
        onPageSize={(size) => {
          setPageSize(size);
          setPage(0);
        }}
      />

      {visible.length === 0 ? (
        <div className="flex h-[300px] flex-col items-center justify-center gap-3 rounded-xl border bg-card text-muted-foreground shadow-sm">
          <div className="rounded-full bg-muted p-4">
            <AlertCircle className="size-8" />
          </div>
          <p className="text-sm font-medium">No schedules found</p>
          <p className="text-sm">
            {schedules.length > 0
              ? "Try adjusting your search"
              : "Generate a schedule to get started"}
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {visible.map((group) => (
            <DatasetGroup
              key={group.datasetId}
              group={group}
              open={expanded.has(group.datasetId)}
              onToggle={() => toggle(group.datasetId)}
              onDelete={onDelete}
            />
          ))}
        </div>
      )}

      <PaginationBar {...bar} />
    </div>
  );
}
