import { AlertCircle } from "lucide-react";

interface EmptyStateProps {
  hasData: boolean;
}

/**
 * EmptyState - Display when no results found
 */
export function EmptyState({ hasData }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 text-muted-foreground h-[400px]">
      <div className="rounded-full bg-muted p-4">
        <AlertCircle className="size-8" />
      </div>
      <div className="space-y-1 text-center">
        <p className="text-base font-medium text-foreground">No exams found</p>
        {hasData ? (
          <p className="text-sm">Try adjusting your search or filters</p>
        ) : (
          <p className="text-sm">Upload a dataset to get started</p>
        )}
      </div>
    </div>
  );
}
