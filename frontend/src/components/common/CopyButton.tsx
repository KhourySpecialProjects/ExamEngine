import { Check, Copy } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

/** Copies text to the clipboard; `copied` is true for ~1s afterwards. */
export function useCopy() {
  const [copied, setCopied] = useState(false);
  const timer = useRef<number | undefined>(undefined);
  useEffect(() => () => window.clearTimeout(timer.current), []);

  async function copy(value: string) {
    try {
      await navigator.clipboard.writeText(value);
    } catch {
      toast.error("Couldn't copy to the clipboard");
      return;
    }
    setCopied(true);
    window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => setCopied(false), 1000);
  }

  return { copied, copy };
}

/**
 * Small icon button that copies `value` exactly (IDs keep leading zeros).
 * Never lets the click reach a parent (e.g. a clickable pill).
 */
export function CopyButton({
  value,
  label,
  className,
}: {
  value: string;
  /** Accessible name, e.g. "Copy CRN 20020". */
  label: string;
  className?: string;
}) {
  const { copied, copy } = useCopy();
  const Icon = copied ? Check : Copy;
  return (
    <button
      type="button"
      aria-label={label}
      title={label}
      onClick={(e) => {
        e.stopPropagation();
        void copy(value);
      }}
      className={cn(
        "inline-flex shrink-0 items-center justify-center rounded-sm p-0.5 opacity-60 hover:opacity-100 focus-visible:opacity-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
        className,
      )}
    >
      <Icon className="size-3" aria-hidden />
    </button>
  );
}
