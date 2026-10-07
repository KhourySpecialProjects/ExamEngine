import type { ReactNode } from "react";

/** Collapsed by default so a long list never pushes the page down. */
export function Collapsible({
  summary,
  children,
}: {
  summary: string;
  children: ReactNode;
}) {
  return (
    <details className="text-xs">
      <summary className="cursor-pointer font-medium">{summary}</summary>
      <div className="mt-2 max-h-48 overflow-y-auto">{children}</div>
    </details>
  );
}
