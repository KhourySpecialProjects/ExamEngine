"use client";

import { ChevronRight, MoveLeft } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { ViewTabSwitcher } from "@/components/common/ViewTabSwitcher";
import { Button } from "@/components/ui/button";
import CompactView from "@/components/visualization/calendar/CompactView";
import DensityView from "@/components/visualization/calendar/DensityView";
import { ExamListDialog } from "@/components/visualization/calendar/ExamListDialog";
import ListView from "@/components/visualization/list/ListView";
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb";
import Link from "next/link";

type ViewType = "density" | "compact" | "list";

export default function SchedulePage({ params }: { params: { id: string } }) {
  const [activeView, setActiveView] = useState<ViewType>("density");
  const router = useRouter();

  return (
    <div className="space-y-6 m-5">
      <div className="flex items-center gap-4 mb-6">
        <Button
          variant="outline"
          size="sm"
          className="rounded-md"
          onClick={() => router.push("/dashboard")}
        >
          <MoveLeft />
          Back
        </Button>
        <Breadcrumb>
          <BreadcrumbList>
            <BreadcrumbItem>
              <BreadcrumbLink asChild>
                <Link href="/dashboard">Schedules</Link>
              </BreadcrumbLink>
            </BreadcrumbItem>
            <BreadcrumbSeparator>
              <ChevronRight className="h-4 w-4" />
            </BreadcrumbSeparator>
            <BreadcrumbItem>
              {/* TODO: replace with schedule name */}
              <BreadcrumbPage>2025 Fall Schedule</BreadcrumbPage>
            </BreadcrumbItem>
          </BreadcrumbList>
        </Breadcrumb>
      </div>
      <div className="flex items-center justify-between">
        <ViewTabSwitcher activeView={activeView} onViewChange={setActiveView} />
      </div>

      {activeView === "density" && <DensityView />}
      {activeView === "compact" && <CompactView />}
      {activeView === "list" && <ListView />}

      <ExamListDialog />
    </div>
  );
}
