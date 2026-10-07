import { Check, ChevronsUpDown } from "lucide-react";
import { useState } from "react";
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
import { cn } from "@/lib/utils";

export interface LookupOption {
  value: string;
  /** Shown after the value, e.g. "capacity 40 · 3 exams". */
  detail?: string;
}

/** Options containing `query` (case-insensitive), those starting with it first. */
export function filterOptions(
  options: LookupOption[],
  query: string,
): LookupOption[] {
  const q = query.trim().toLowerCase();
  if (!q) return options;
  const starts: LookupOption[] = [];
  const contains: LookupOption[] = [];
  for (const option of options) {
    const value = option.value.toLowerCase();
    if (value.startsWith(q)) starts.push(option);
    else if (value.includes(q)) contains.push(option);
  }
  return [...starts, ...contains];
}

/**
 * A searchable, scrollable list to pick one value. Filtering is done here
 * (not by cmdk) so a long list only renders its first `limit` matches.
 */
export function LookupCombobox({
  label,
  options,
  value,
  onSelect,
  placeholder,
  searchPlaceholder,
  emptyText,
  limit,
}: {
  /** Accessible name of the trigger, e.g. "Instructor". */
  label: string;
  options: LookupOption[];
  value: string | null;
  onSelect: (value: string) => void;
  placeholder: string;
  searchPlaceholder: string;
  emptyText: string;
  limit?: number;
}) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const matches = filterOptions(options, query);
  const shown = limit ? matches.slice(0, limit) : matches;
  const hidden = matches.length - shown.length;

  return (
    <Popover
      open={open}
      onOpenChange={(next) => {
        setOpen(next);
        if (!next) setQuery("");
      }}
    >
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          role="combobox"
          aria-expanded={open}
          aria-label={label}
          className="w-72 justify-between font-normal"
        >
          <span className={cn("truncate", !value && "text-muted-foreground")}>
            {value ?? placeholder}
          </span>
          <ChevronsUpDown className="opacity-50" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-80 p-0" align="start">
        <Command shouldFilter={false}>
          <CommandInput
            placeholder={searchPlaceholder}
            value={query}
            onValueChange={setQuery}
          />
          <CommandList className="max-h-72">
            <CommandEmpty>{emptyText}</CommandEmpty>
            <CommandGroup>
              {shown.map((option) => (
                <CommandItem
                  key={option.value}
                  value={option.value}
                  onSelect={() => {
                    onSelect(option.value);
                    setOpen(false);
                    setQuery("");
                  }}
                >
                  <Check
                    className={cn(
                      "size-4",
                      option.value === value ? "opacity-100" : "opacity-0",
                    )}
                  />
                  <span className="font-mono">{option.value}</span>
                  {option.detail && (
                    <span className="ml-auto text-xs text-muted-foreground">
                      {option.detail}
                    </span>
                  )}
                </CommandItem>
              ))}
            </CommandGroup>
            {hidden > 0 && (
              <p className="px-3 py-2 text-xs text-muted-foreground">
                {hidden} more: type to narrow the list.
              </p>
            )}
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
}
