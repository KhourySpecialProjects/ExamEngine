"use client";

import {
  AlertTriangle,
  CheckCircle2,
  Circle,
  Loader2,
  ShieldCheck,
  XCircle,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { apiClient } from "@/lib/api/client";
import type {
  ValidationCategory,
  ValidationCheck,
  ValidationEvent,
  ValidationResult,
} from "@/lib/api/validation";
import { cn } from "@/lib/utils";

interface ValidateScheduleDialogProps {
  scheduleId: string;
  scheduleName?: string;
}

type RowState = { status: "pending" | "running" } | ValidationResult;
type RowStatus = RowState["status"];
type DoneEvent = Extract<ValidationEvent, { type: "done" }>;

const CATEGORY_TITLES: Record<ValidationCategory, string> = {
  coverage: "Coverage",
  rooms: "Rooms",
  groups: "Combined & common groups",
  conflicts: "Conflicts",
  data: "Data consistency",
};

const CATEGORY_ORDER = Object.keys(CATEGORY_TITLES) as ValidationCategory[];

const STATUS_STYLES: Record<
  RowStatus,
  { icon: typeof Circle; className: string; iconClassName?: string }
> = {
  pending: { icon: Circle, className: "text-muted-foreground" },
  running: {
    icon: Loader2,
    className: "text-foreground",
    iconClassName: "animate-spin",
  },
  pass: { icon: CheckCircle2, className: "text-green-600" },
  warn: { icon: AlertTriangle, className: "text-amber-600" },
  skipped: { icon: AlertTriangle, className: "text-amber-600" },
  fail: { icon: XCircle, className: "text-red-600" },
};

const PENDING: RowState = { status: "pending" };

function plural(count: number, noun: string): string {
  return `${count} ${noun}${count === 1 ? "" : "s"}`;
}

function totalsText({ counts }: DoneEvent): string {
  const total = counts.pass + counts.warn + counts.fail + counts.skipped;
  return [
    plural(total, "check"),
    `${counts.pass} passed`,
    plural(counts.warn, "warning"),
    `${counts.fail} failed`,
    `${counts.skipped} skipped`,
  ].join(" · ");
}

/** Rows a failed run left mid-check go back to "not run". */
function resetRunning(
  rows: Record<string, RowState>,
): Record<string, RowState> {
  return Object.fromEntries(
    Object.entries(rows).filter(([, row]) => row.status !== "running"),
  );
}

export function ValidateScheduleDialog({
  scheduleId,
  scheduleName,
}: ValidateScheduleDialogProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [checks, setChecks] = useState<ValidationCheck[] | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [rows, setRows] = useState<Record<string, RowState>>({});
  const [isRunning, setIsRunning] = useState(false);
  const [hasRun, setHasRun] = useState(false);
  const [runError, setRunError] = useState<string | null>(null);
  const [totals, setTotals] = useState<DoneEvent | null>(null);
  // The in-flight run; events from any other (aborted) run are ignored.
  const runRef = useRef<AbortController | null>(null);

  useEffect(() => {
    if (!isOpen) return;
    let cancelled = false;
    setChecks(null);
    setLoadError(null);
    apiClient.validation.getChecks().then(
      (catalog) => {
        if (!cancelled) setChecks(catalog);
      },
      (error) => {
        if (cancelled) return;
        setLoadError(error instanceof Error ? error.message : "Unknown error");
      },
    );
    return () => {
      cancelled = true;
    };
  }, [isOpen]);

  useEffect(() => () => runRef.current?.abort(), []);

  const handleOpenChange = (open: boolean) => {
    runRef.current?.abort();
    runRef.current = null;
    setIsRunning(false);
    setHasRun(false);
    setRows({});
    setTotals(null);
    setRunError(null);
    setIsOpen(open);
  };

  const handleRun = async () => {
    const controller = new AbortController();
    runRef.current = controller;
    setRows({});
    setTotals(null);
    setRunError(null);
    setIsRunning(true);
    setHasRun(true);

    let finished = false;
    const fail = (message: string) => {
      setRunError(message);
      setRows(resetRunning);
      toast.error("Validation failed", { description: message });
    };

    try {
      await apiClient.validation.runValidation(
        scheduleId,
        (event) => {
          if (runRef.current !== controller) return;
          switch (event.type) {
            case "start":
              setRows((prev) => ({
                ...prev,
                [event.check_id]: { status: "running" },
              }));
              break;
            case "result":
              setRows((prev) => ({ ...prev, [event.check_id]: event }));
              break;
            case "done":
              finished = true;
              setTotals(event);
              break;
            case "error":
              finished = true;
              fail(event.message);
              break;
          }
        },
        controller.signal,
      );
      if (!finished && runRef.current === controller) {
        fail("The validation stream ended before all checks finished");
      }
    } catch (error) {
      if (controller.signal.aborted) return;
      fail(error instanceof Error ? error.message : "Unknown error");
    } finally {
      if (runRef.current === controller) {
        runRef.current = null;
        setIsRunning(false);
      }
    }
  };

  const groups = CATEGORY_ORDER.map((category) => ({
    category,
    checks: (checks ?? []).filter((check) => check.category === category),
  })).filter((group) => group.checks.length > 0);

  return (
    <Dialog open={isOpen} onOpenChange={handleOpenChange}>
      <DialogTrigger asChild>
        <Button variant="outline">
          <ShieldCheck className="mr-2 h-4 w-4" />
          Validate Schedule
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-3xl">
        <DialogHeader>
          <DialogTitle>
            Validate Schedule{scheduleName ? `: ${scheduleName}` : ""}
          </DialogTitle>
          <DialogDescription>
            Independently re-checks this schedule against the dataset&apos;s
            original uploaded files. Nothing is changed.
          </DialogDescription>
        </DialogHeader>

        {loadError ? (
          <p className="text-sm text-destructive">
            Failed to load checks: {loadError}
          </p>
        ) : checks === null ? (
          <div className="flex items-center justify-center py-8">
            <Loader2
              aria-label="Loading checks"
              className="h-6 w-6 animate-spin text-muted-foreground"
            />
          </div>
        ) : (
          <>
            <div className="flex items-center gap-3">
              <Button onClick={handleRun} disabled={isRunning}>
                {isRunning ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <ShieldCheck className="mr-2 h-4 w-4" />
                )}
                {isRunning
                  ? "Running…"
                  : hasRun
                    ? "Run Again"
                    : "Run Validation"}
              </Button>
              {runError && (
                <p role="alert" className="text-sm text-destructive">
                  Validation failed: {runError}
                </p>
              )}
            </div>

            <div className="max-h-[70vh] space-y-5 overflow-y-auto pr-2">
              {groups.map((group) => (
                <section key={group.category} className="space-y-2">
                  <h3 className="text-sm font-semibold">
                    {CATEGORY_TITLES[group.category]}
                  </h3>
                  <ul className="space-y-2">
                    {group.checks.map((check) => (
                      <CheckRow
                        key={check.id}
                        check={check}
                        row={rows[check.id] ?? PENDING}
                      />
                    ))}
                  </ul>
                </section>
              ))}
            </div>
          </>
        )}

        {totals && (
          <DialogFooter className="text-sm text-muted-foreground sm:justify-start">
            <span>{totalsText(totals)}</span>
            <span>({(totals.duration_ms / 1000).toFixed(1)}s)</span>
          </DialogFooter>
        )}
      </DialogContent>
    </Dialog>
  );
}

function CheckRow({ check, row }: { check: ValidationCheck; row: RowState }) {
  const style = STATUS_STYLES[row.status];
  const Icon = style.icon;
  return (
    <li
      data-testid={`check-${check.id}`}
      data-status={row.status}
      className={cn("flex gap-3", style.className)}
    >
      <Icon className={cn("mt-0.5 h-4 w-4 shrink-0", style.iconClassName)} />
      <div className="min-w-0 space-y-1">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium">{check.title}</span>
          {row.status === "skipped" && (
            <Badge variant="outline" className="text-amber-600">
              Skipped
            </Badge>
          )}
        </div>
        <p className="text-xs opacity-75">{check.description}</p>
        {"summary" in row && <ResultDetails result={row} />}
      </div>
    </li>
  );
}

function ResultDetails({ result }: { result: ValidationResult }) {
  const more = result.count - result.examples.length;
  return (
    <div className="space-y-1 text-sm">
      <p>{result.summary}</p>
      {result.examples.length > 0 && (
        <details className="text-xs">
          <summary className="cursor-pointer select-none">
            {plural(result.examples.length, "example")}
          </summary>
          <ul className="mt-1 list-disc space-y-0.5 pl-5 font-mono">
            {result.examples.map((example, index) => (
              // Examples can repeat; their position is their identity.
              // biome-ignore lint/suspicious/noArrayIndexKey: static list
              <li key={index}>{example}</li>
            ))}
          </ul>
          {more > 0 && <p className="mt-1 pl-5">and {more} more</p>}
        </details>
      )}
    </div>
  );
}
