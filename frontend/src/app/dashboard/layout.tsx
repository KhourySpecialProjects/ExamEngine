"use client";

import { DashboardSidebar } from "@/components/layouts/DashboardSidebar";
import { DashboardHeader } from "@/components/layouts/DashboardHeader";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="h-screen flex flex-col">
      {/* Header - Fixed at top */}
      <DashboardHeader />

      {/* Main Content - Sidebar + Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Sidebar - Fixed width, scrollable */}
        <aside className="w-80 border-r bg-white overflow-y-auto">
          <DashboardSidebar />
        </aside>

        {/* Main Content Area - Flexible, scrollable */}
        <main className="flex-1 overflow-y-auto bg-gray-50">{children}</main>
      </div>
    </div>
  );
}
