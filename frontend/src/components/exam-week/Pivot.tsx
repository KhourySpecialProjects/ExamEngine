import type { ReactNode } from "react";

/** A value in an exam list or week that switches what Explore looks up. */
export function Pivot({
  label,
  onClick,
  children,
}: {
  /** Accessible name, e.g. "Explore room Hall". */
  label: string;
  onClick: () => void;
  children: ReactNode;
}) {
  return (
    <button
      type="button"
      aria-label={label}
      title={label}
      onClick={onClick}
      className="cursor-pointer underline decoration-dotted underline-offset-2 hover:text-primary"
    >
      {children}
    </button>
  );
}
