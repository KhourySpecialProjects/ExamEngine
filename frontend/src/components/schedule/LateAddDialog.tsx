"use client";

import { CalendarPlus, Loader2, Search } from "lucide-react";
import { type ComponentProps, type FormEvent, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { apiClient } from "@/lib/api/client";
import type { LateAddInput, LateAddSearchResult } from "@/lib/api/schedules";
import { LateAddResults, slotKey } from "./LateAddResults";

interface LateAddDialogProps {
  scheduleId: string;
  scheduleName?: string;
  /** The dataset's uploaded files are gone, so nothing can be searched. */
  datasetDeleted?: boolean;
}

const DELETED_REASON =
  "The dataset this schedule came from was deleted, so its uploaded files are no longer available.";

const EMPTY_INPUT: LateAddInput = {
  crn: "",
  course_code: "",
  instructor_id: "",
};

const FIELDS: { id: keyof LateAddInput; label: string }[] = [
  { id: "crn", label: "CRN" },
  { id: "course_code", label: "Course code" },
  { id: "instructor_id", label: "Instructor ID" },
];

// DialogTrigger (asChild) passes its handlers and ref through these props.
function TriggerButton(props: ComponentProps<typeof Button>) {
  return (
    <Button variant="outline" {...props}>
      <CalendarPlus className="mr-2 h-4 w-4" />
      Late Add
    </Button>
  );
}

/** Finds blocks for an exam that missed generation. Read-only: nothing is saved. */
export function LateAddDialog({
  scheduleId,
  scheduleName,
  datasetDeleted = false,
}: LateAddDialogProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [input, setInput] = useState<LateAddInput>(EMPTY_INPUT);
  const [isSearching, setIsSearching] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<LateAddSearchResult | null>(null);
  const [selectedSlot, setSelectedSlot] = useState<string | null>(null);
  const [rooms, setRooms] = useState<Record<string, string>>({});
  // Bumped per search and on close: a reply to an older one is dropped.
  const searchRef = useRef(0);

  if (datasetDeleted) {
    // A disabled button gets no hover in some browsers: the wrapper shows
    // the reason instead.
    return (
      <span title={DELETED_REASON} className="cursor-not-allowed">
        <TriggerButton disabled />
      </span>
    );
  }

  const handleOpenChange = (open: boolean) => {
    searchRef.current += 1;
    setInput(EMPTY_INPUT);
    setIsSearching(false);
    setError(null);
    setResult(null);
    setSelectedSlot(null);
    setRooms({});
    setIsOpen(open);
  };

  const handleSearch = async (event: FormEvent) => {
    event.preventDefault();
    const search = ++searchRef.current;
    setIsSearching(true);
    setError(null);
    setResult(null);
    setSelectedSlot(null);
    setRooms({});
    try {
      const found = await apiClient.schedules.lateAddSearch(scheduleId, input);
      if (searchRef.current !== search) return;
      setResult(found);
      setSelectedSlot(
        found.candidates[0] ? slotKey(found.candidates[0]) : null,
      );
    } catch (err) {
      if (searchRef.current !== search) return;
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      if (searchRef.current === search) setIsSearching(false);
    }
  };

  const incomplete = FIELDS.some(({ id }) => !input[id].trim());

  return (
    <Dialog open={isOpen} onOpenChange={handleOpenChange}>
      <DialogTrigger asChild>
        <TriggerButton />
      </DialogTrigger>
      <DialogContent className="sm:max-w-4xl">
        <DialogHeader>
          <DialogTitle>
            Late Add{scheduleName ? `: ${scheduleName}` : ""}
          </DialogTitle>
          <DialogDescription>
            Finds blocks for an exam that is not in this schedule, using only
            rooms that are free and not blocked out. No scheduled exam moves and
            nothing is saved.
          </DialogDescription>
        </DialogHeader>

        <form
          onSubmit={handleSearch}
          className="flex flex-wrap items-end gap-3"
          aria-label="Late add exam"
        >
          {FIELDS.map(({ id, label }) => (
            <div key={id} className="space-y-1">
              <Label htmlFor={`late-add-${id}`}>{label}</Label>
              <Input
                id={`late-add-${id}`}
                value={input[id]}
                onChange={(e) => setInput({ ...input, [id]: e.target.value })}
                autoComplete="off"
                className="w-40"
              />
            </div>
          ))}
          <Button type="submit" disabled={incomplete || isSearching}>
            {isSearching ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Search className="mr-2 h-4 w-4" />
            )}
            {isSearching ? "Searching…" : "Find blocks"}
          </Button>
          {error && (
            <p role="alert" className="basis-full text-sm text-destructive">
              {error}
            </p>
          )}
        </form>

        {result && (
          <div className="max-h-[60vh] overflow-y-auto pr-2">
            <LateAddResults
              result={result}
              selectedSlot={selectedSlot}
              rooms={rooms}
              onSelect={setSelectedSlot}
              onRoomChange={(slot, room) =>
                setRooms((prev) => ({ ...prev, [slot]: room }))
              }
            />
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
