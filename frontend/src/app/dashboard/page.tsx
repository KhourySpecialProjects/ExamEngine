"use client";

import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";

export default function DashboardPage() {
  const router = useRouter();
  return (
    <div className="space-y-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Schedules</h1>
          <p className="text-muted-foreground">
            Manage and compare your exam schedules
          </p>
          <Button
            onClick={() => router.push("/dashboard/123")}
            variant="outline"
          >
            Navigate to /dashboard/123
          </Button>
        </div>
      </div>
    </div>
  );
}
