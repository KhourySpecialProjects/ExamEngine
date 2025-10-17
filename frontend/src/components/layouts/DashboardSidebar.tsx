"use client";

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Database } from "lucide-react";
import { Uploader } from "../upload/Uploader";

export function DashboardSidebar() {
  return (
    <div className="p-6 space-y-6">
      <section>
        <div className="flex items-center gap-2 mb-3">
          <Database className="text-green-800" />
          <h2 className="font-semibold text-sm">Data Management</h2>
        </div>

        {/* Dataset Selector */}
        <Select defaultValue="spring2024">
          <SelectTrigger className="mb-3 w-full">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="spring2024">Spring 2024 Dataset</SelectItem>
            <SelectItem value="fall2023">Fall 2023 Dataset</SelectItem>
          </SelectContent>
        </Select>

        {/* Upload Button */}
        <Uploader />

        {/* Dataset Info */}
        <div className="mt-3 text-sm text-muted-foreground">
          <div className="font-medium text-foreground">Current Dataset</div>
          <div>1247 courses</div>
          <div>Last Updated: 2h ago</div>
        </div>
      </section>
    </div>
  );
}
