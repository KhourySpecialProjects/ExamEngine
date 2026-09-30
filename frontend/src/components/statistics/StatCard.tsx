import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

/** One headline number with a short explanation underneath. */
export function StatCard({
  title,
  icon: Icon,
  value,
  detail,
}: {
  title: string;
  icon: LucideIcon;
  value: ReactNode;
  detail?: ReactNode;
}) {
  return (
    <Card className="gap-2">
      <CardHeader className="flex flex-row items-center justify-between space-y-0">
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
        <Icon className="h-4 w-4 text-muted-foreground" aria-hidden />
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold tabular-nums">{value}</div>
        {detail && <p className="text-xs text-muted-foreground">{detail}</p>}
      </CardContent>
    </Card>
  );
}

/** Label + number pairs inside one card, e.g. combined exam groups. */
export function StatGroupCard({
  title,
  icon: Icon,
  items,
}: {
  title: string;
  icon: LucideIcon;
  items: { label: string; value: number }[];
}) {
  return (
    <Card className="gap-2">
      <CardHeader className="flex flex-row items-center justify-between space-y-0">
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
        <Icon className="h-4 w-4 text-muted-foreground" aria-hidden />
      </CardHeader>
      <CardContent>
        <dl className="grid grid-cols-3 gap-2">
          {items.map(({ label, value }) => (
            // Number shown above its label; dt must come first in the DOM.
            <div key={label} className="flex flex-col-reverse">
              <dt className="text-xs text-muted-foreground">{label}</dt>
              <dd className="text-2xl font-bold tabular-nums">
                {value.toLocaleString()}
              </dd>
            </div>
          ))}
        </dl>
      </CardContent>
    </Card>
  );
}
