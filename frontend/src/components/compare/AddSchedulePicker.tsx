import { Plus } from "lucide-react";
import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { useSchedulesStore } from "@/lib/store/schedulesStore";

/** Search the user's own and shared completed schedules and add one as a column. */
export function AddSchedulePicker({
  exclude,
  onAdd,
}: {
  /** Ids already shown. */
  exclude: readonly string[];
  onAdd: (id: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const schedules = useSchedulesStore((state) => state.schedules);
  const isLoading = useSchedulesStore((state) => state.isLoadingList);
  const fetchSchedules = useSchedulesStore((state) => state.fetchSchedules);

  const choices = schedules.filter(
    (s) => s.status === "Completed" && !exclude.includes(s.schedule_id),
  );

  return (
    <Popover
      open={open}
      onOpenChange={(next) => {
        setOpen(next);
        if (next) fetchSchedules();
      }}
    >
      <PopoverTrigger asChild>
        <Button variant="outline" size="sm">
          <Plus className="h-4 w-4" />
          Add schedule
        </Button>
      </PopoverTrigger>
      <PopoverContent align="end" className="w-80 p-0">
        <Command>
          <CommandInput placeholder="Search schedules..." />
          <CommandList>
            <CommandEmpty>
              {isLoading ? "Loading schedules..." : "No schedule found."}
            </CommandEmpty>
            <CommandGroup>
              {choices.map((s) => (
                <CommandItem
                  key={s.schedule_id}
                  value={`${s.schedule_name} ${s.dataset.name} ${s.schedule_id}`}
                  onSelect={() => {
                    onAdd(s.schedule_id);
                    setOpen(false);
                  }}
                >
                  <div className="min-w-0 flex-1">
                    <div className="truncate">{s.schedule_name}</div>
                    <div className="truncate text-xs text-muted-foreground">
                      {s.dataset.name}
                    </div>
                  </div>
                  {s.is_shared && !s.is_owner && (
                    <Badge variant="outline">Shared</Badge>
                  )}
                </CommandItem>
              ))}
            </CommandGroup>
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
}
