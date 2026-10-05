import { CalendarPlus } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

/** Marks a late-added exam, or a schedule saved by a late add. */
export function LateAddBadge({
  title,
  className,
}: {
  title?: string;
  className?: string;
}) {
  return (
    <Badge
      variant="outline"
      className={cn(
        "gap-1 border-amber-300 bg-amber-50/50 px-1.5 py-0.5 text-xs text-amber-800",
        className,
      )}
      title={title}
    >
      <CalendarPlus className="h-3 w-3" />
      Late add
    </Badge>
  );
}
