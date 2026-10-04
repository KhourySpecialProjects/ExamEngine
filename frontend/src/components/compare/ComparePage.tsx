"use client";

import { AlertTriangle, ChevronRight, MoveLeft } from "lucide-react";
import Link from "next/link";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { COLUMN_COLORS, columnLetter } from "@/lib/compare";
import { useCompare } from "@/lib/hooks/useCompare";
import { MAX_COMPARED } from "@/lib/scheduleSelection";
import { AddSchedulePicker } from "./AddSchedulePicker";
import { CalendarShapeSection } from "./CalendarShapeSection";
import { CompareGrid, type GridColumn, shownColumns } from "./CompareGrid";
import { CompareHeader } from "./CompareHeader";
import {
  ConflictsSection,
  PublishableSection,
  RoomsSection,
  SettingsSection,
} from "./CompareSections";

function CompareSkeleton({ count }: { count: number }) {
  return (
    <div className="space-y-4" aria-busy>
      <span className="sr-only">Loading schedules</span>
      <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: count }, (_, i) => (
          // biome-ignore lint/suspicious/noArrayIndexKey: placeholders have no identity
          <div key={i} className="h-20 animate-pulse rounded-lg bg-muted" />
        ))}
      </div>
      {[0, 1, 2].map((i) => (
        <div key={i} className="h-32 animate-pulse rounded-lg bg-muted" />
      ))}
    </div>
  );
}

function DifferentDatasetsBanner({ columns }: { columns: GridColumn[] }) {
  const datasets = new Map(
    shownColumns(columns).map((c) => [
      c.schedule.dataset.dataset_id,
      c.schedule.dataset.dataset_name,
    ]),
  );
  if (datasets.size < 2) return null;
  return (
    <Alert>
      <AlertTriangle className="h-4 w-4" />
      <AlertTitle>These schedules use different datasets</AlertTitle>
      <AlertDescription>
        {[...datasets.values()].join(", ")}. Differences can come from the data
        as well as from the settings.
      </AlertDescription>
    </Alert>
  );
}

/** Up to 4 schedules side by side; the URL holds the columns, baseline first. */
export function ComparePage() {
  const compare = useCompare();
  const { ids, base, loading, error } = compare;

  const columns: GridColumn[] = compare.columns.map(({ id, item }, i) => ({
    id,
    letter: columnLetter(i),
    color: COLUMN_COLORS[i],
    schedule: item?.status === "ok" ? item : null,
    isBaseline: id === base,
  }));
  const shown = shownColumns(columns);
  const unavailable = compare.columns.filter(
    (c) => c.item?.status === "unavailable",
  );

  let body: React.ReactNode;
  if (error) {
    body = (
      <Alert variant="destructive">
        <AlertTriangle className="h-4 w-4" />
        <AlertTitle>Couldn't load the schedules</AlertTitle>
        <AlertDescription>
          <p>{error}</p>
          <Button variant="outline" size="sm" onClick={compare.retry}>
            Try again
          </Button>
        </AlertDescription>
      </Alert>
    );
  } else if (loading) {
    body = <CompareSkeleton count={Math.max(ids.length, 2)} />;
  } else if (shown.length < 2) {
    const remaining = shown[0]?.schedule.schedule_name;
    body = (
      <Card>
        <CardContent className="space-y-4 py-6 text-center">
          <p className="text-lg font-semibold">
            {remaining
              ? `Add a schedule to compare with ${remaining}`
              : "Pick at least two schedules to compare"}
          </p>
          <p className="text-sm text-muted-foreground">
            Select schedules on the{" "}
            <Link href="/dashboard" className="underline">
              Schedules
            </Link>{" "}
            page, or add them here.
          </p>
          {unavailable.length > 0 && (
            <p className="text-sm text-muted-foreground">
              {unavailable.length === 1
                ? "1 linked schedule is not available"
                : `${unavailable.length} linked schedules are not available`}{" "}
              (it may have been deleted or not shared with you).{" "}
              <button
                type="button"
                className="underline"
                onClick={() => compare.remove(...unavailable.map((c) => c.id))}
              >
                Remove
              </button>
            </p>
          )}
          <div className="flex justify-center">
            <AddSchedulePicker exclude={ids} onAdd={compare.add} />
          </div>
        </CardContent>
      </Card>
    );
  } else {
    body = (
      <CompareGrid columns={columns}>
        <div className="space-y-4">
          <DifferentDatasetsBanner columns={columns} />
          <CompareHeader actions={compare} />
          <SettingsSection />
          <PublishableSection />
          <ConflictsSection />
          <CalendarShapeSection />
          <RoomsSection />
        </div>
      </CompareGrid>
    );
  }

  return (
    <div className="m-5 space-y-4">
      <div className="flex flex-wrap items-center gap-4">
        <Button variant="outline" size="sm" className="rounded-md" asChild>
          <Link href="/dashboard">
            <MoveLeft />
            Back
          </Link>
        </Button>
        <Breadcrumb>
          <BreadcrumbList>
            <BreadcrumbItem>
              <BreadcrumbLink asChild>
                <Link href="/dashboard">Schedules</Link>
              </BreadcrumbLink>
            </BreadcrumbItem>
            <BreadcrumbSeparator>
              <ChevronRight className="h-4 w-4" />
            </BreadcrumbSeparator>
            <BreadcrumbItem>
              <BreadcrumbPage>Compare</BreadcrumbPage>
            </BreadcrumbItem>
          </BreadcrumbList>
        </Breadcrumb>
        <div className="flex-1" />
        {shown.length >= 2 && ids.length < MAX_COMPARED && (
          <AddSchedulePicker exclude={ids} onAdd={compare.add} />
        )}
      </div>
      {body}
    </div>
  );
}
