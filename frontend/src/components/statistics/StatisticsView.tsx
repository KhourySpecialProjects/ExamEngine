import {
  Ban,
  BookOpen,
  Building2,
  Clock,
  GitMerge,
  Layers,
  Users,
} from "lucide-react";
import {
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useConflictDataSimple } from "@/lib/hooks/useConflictDataSimple";
import { useScheduleStats } from "@/lib/hooks/useScheduleStats";
import { useSchedulesStore } from "@/lib/store/schedulesStore";
import { DistributionCharts } from "./DistributionCharts";
import { ProblemsSection } from "./ProblemsSection";
import { StatCard, StatGroupCard } from "./StatCard";

/**
 * Statistics tab: problems first, then the overview, exam groups and room
 * constraints, then how exams are spread over the exam period.
 */
export function StatisticsView({
  onShowConflicts,
}: {
  /** Switches the schedule page to the Conflicts tab. */
  onShowConflicts?: () => void;
}) {
  const currentSchedule = useSchedulesStore((state) => state.currentSchedule);
  const stats = useScheduleStats(currentSchedule);
  // Same people counts as the Conflicts tab's summary cards.
  const { metrics: conflicts } = useConflictDataSimple();

  if (!stats) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Statistics Dashboard</CardTitle>
          <CardDescription>
            Generate a schedule to view statistics
          </CardDescription>
        </CardHeader>
      </Card>
    );
  }

  const placedPercent =
    stats.totalExams > 0
      ? Math.round((stats.placedExams / stats.totalExams) * 1000) / 10
      : 0;
  const groupCards = [
    stats.combined.groups > 0 && (
      <StatGroupCard
        key="combined"
        title="Combined exams"
        icon={GitMerge}
        items={[
          { label: "Groups", value: stats.combined.groups },
          { label: "Sections", value: stats.combined.sections },
          { label: "Students", value: stats.combined.students },
        ]}
      />
    ),
    stats.common.groups > 0 && (
      <StatGroupCard
        key="common"
        title="Common exams"
        icon={Layers}
        items={[
          { label: "Groups", value: stats.common.groups },
          { label: "Sections", value: stats.common.sections },
          { label: "Students", value: stats.common.students },
        ]}
      />
    ),
    stats.blockouts.rooms > 0 && (
      <StatGroupCard
        key="blockouts"
        title="Room blockouts"
        icon={Ban}
        items={[
          { label: "Rooms blocked", value: stats.blockouts.rooms },
          { label: "Blocked slots", value: stats.blockouts.slots },
        ]}
      />
    ),
  ].filter(Boolean);

  return (
    <div className="space-y-6">
      <div className="pl-2">
        <h1 className="text-2xl font-bold">Statistics View</h1>
        <p className="text-muted-foreground">
          Analytics and insights about your exam schedule
        </p>
      </div>

      <ProblemsSection
        stats={stats}
        conflicts={conflicts}
        onShowConflicts={onShowConflicts}
      />

      <section aria-labelledby="stats-overview" className="space-y-3">
        <h2 id="stats-overview" className="pl-2 text-lg font-semibold">
          Overview
        </h2>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <StatCard
            title="Exams scheduled"
            icon={BookOpen}
            value={`${stats.placedExams.toLocaleString()} / ${stats.totalExams.toLocaleString()}`}
            detail={`${placedPercent}% have a day, time and room`}
          />
          <StatCard
            title="Students"
            icon={Users}
            value={stats.uniqueStudents?.toLocaleString() ?? "—"}
            detail={
              stats.uniqueStudents == null
                ? "Dataset details not available"
                : "Unique students enrolled"
            }
          />
          <StatCard
            title="Room utilization"
            icon={Building2}
            value={`${stats.roomUtilization}%`}
            detail={`Average seats filled across ${stats.roomsUsed.toLocaleString()} rooms used`}
          />
          <StatCard
            title="Time slots used"
            icon={Clock}
            value={stats.slotsUsed.toLocaleString()}
            detail="Day and block pairs with at least one exam"
          />
        </div>
      </section>

      {groupCards.length > 0 && (
        <section aria-labelledby="stats-groups" className="space-y-3">
          <h2 id="stats-groups" className="pl-2 text-lg font-semibold">
            Exam groups and room constraints
          </h2>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {groupCards}
          </div>
        </section>
      )}

      <DistributionCharts stats={stats} />
    </div>
  );
}
