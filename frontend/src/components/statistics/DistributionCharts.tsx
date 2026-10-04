import type { ReactElement } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import type { ScheduleSummary } from "@/lib/api/schedules";

function ChartCard({
  title,
  description,
  empty,
  children,
}: {
  title: string;
  description: string;
  empty: boolean;
  children: ReactElement;
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent>
        {empty ? (
          <div className="flex h-[260px] items-center justify-center text-muted-foreground">
            No scheduled exams
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={260}>
            {children}
          </ResponsiveContainer>
        )}
      </CardContent>
    </Card>
  );
}

/** How placed exams spread over days and time blocks (same chart style). */
export function DistributionCharts({
  calendar,
}: {
  calendar: ScheduleSummary["calendar"];
}) {
  const empty = calendar.days.length === 0;
  return (
    <section aria-labelledby="stats-distribution" className="space-y-3">
      <h2 id="stats-distribution" className="pl-2 text-lg font-semibold">
        Distribution
      </h2>
      <div className="grid gap-4 md:grid-cols-2">
        <ChartCard
          title="Exams per day"
          description="Scheduled exams on each day"
          empty={empty}
        >
          <BarChart data={calendar.days}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="day" interval={0} />
            <YAxis allowDecimals={false} />
            <Tooltip />
            <Bar dataKey="exams" name="Exams" fill="#3b82f6" />
          </BarChart>
        </ChartCard>
        <ChartCard
          title="Students taking exams per day"
          description="Enrollment summed over each day's exams; a student with two exams counts twice"
          empty={empty}
        >
          <BarChart data={calendar.days}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="day" interval={0} />
            <YAxis allowDecimals={false} />
            <Tooltip />
            <Bar dataKey="seats" name="Students" fill="#10b981" />
          </BarChart>
        </ChartCard>
      </div>
      <ChartCard
        title="Exams per time block"
        description="Scheduled exams in each block, across all days"
        empty={empty}
      >
        <BarChart data={calendar.blocks}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="label" interval={0} />
          <YAxis allowDecimals={false} />
          <Tooltip />
          <Bar dataKey="exams" name="Exams" fill="#6366f1" />
        </BarChart>
      </ChartCard>
    </section>
  );
}
