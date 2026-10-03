import "@tanstack/react-table";
import type { RowData } from "@tanstack/react-table";

declare module "@tanstack/react-table" {
  // biome-ignore lint/correctness/noUnusedVariables: must match TanStack's generic signature
  interface ColumnMeta<TData extends RowData, TValue> {
    /**
     * Tailwind width class (e.g. "w-[12%]") for tables with a fixed layout,
     * so columns keep their place from page to page.
     */
    width?: string;
  }
}
