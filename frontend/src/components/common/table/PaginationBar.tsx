import {
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { PAGE_SIZES } from "@/lib/store/sessionStorage";

/** "Showing a-b of n", rows per page, and first/previous/next/last buttons. */
export function PaginationBar({
  page,
  pageSize,
  total,
  noun,
  onPage,
  onPageSize,
}: {
  page: number;
  pageSize: number;
  total: number;
  /** Pluralized, with a leading space (" students"), or "". */
  noun: string;
  onPage: (p: number) => void;
  /** Omit to hide the rows-per-page picker. */
  onPageSize?: (size: number) => void;
}) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const start = page * pageSize;
  const end = Math.min(total, start + pageSize);
  const pageButtons = [
    { label: "First page", icon: ChevronsLeft, to: 0 },
    { label: "Previous page", icon: ChevronLeft, to: page - 1 },
    { label: "Next page", icon: ChevronRight, to: page + 1 },
    { label: "Last page", icon: ChevronsRight, to: totalPages - 1 },
  ];
  return (
    <div className="flex flex-wrap items-center justify-between gap-2 py-2">
      <div className="text-sm text-muted-foreground">
        Showing {total === 0 ? 0 : start + 1}-{end} of {total}
        {noun}
      </div>
      <div className="flex items-center gap-2">
        {onPageSize && (
          <>
            <span className="text-sm text-muted-foreground">Rows per page</span>
            <Select
              value={String(pageSize)}
              onValueChange={(v) => onPageSize(Number(v))}
            >
              <SelectTrigger size="sm" aria-label="Rows per page">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {PAGE_SIZES.map((n) => (
                  <SelectItem key={n} value={String(n)}>
                    {n}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </>
        )}
        <span className="text-sm text-muted-foreground tabular-nums">
          Page {page + 1} of {totalPages}
        </span>
        {pageButtons.map(({ label, icon: Icon, to }) => (
          <Button
            key={label}
            variant="outline"
            size="icon-sm"
            aria-label={label}
            title={label}
            disabled={to < 0 || to >= totalPages || to === page}
            onClick={() => onPage(to)}
          >
            <Icon />
          </Button>
        ))}
      </div>
    </div>
  );
}
