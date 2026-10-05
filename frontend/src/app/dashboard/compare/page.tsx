"use client";

import { Suspense } from "react";
import { ComparePage } from "@/components/compare/ComparePage";

// The page reads its columns from the URL (useSearchParams via nuqs).
export default function CompareRoute() {
  return (
    <Suspense>
      <ComparePage />
    </Suspense>
  );
}
