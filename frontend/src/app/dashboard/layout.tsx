"use client";

import { useState } from "react";
import { DashboardHeader } from "@/components/layouts/DashboardHeader";
import { DashboardSidebar } from "@/components/layouts/DashboardSidebar";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);

  return (
    <div className="h-screen flex flex-col">
      {/* Header - Fixed at top */}
      <DashboardHeader />

      {/* Main Content - Sidebar + Content */}
      <div className="relative flex-1 flex overflow-hidden">
        {/* Sidebar - Fixed width, scrollable */}
        <aside
          className={`border-r bg-white overflow-hidden transition-[width] duration-200 ${
            isSidebarOpen ? "w-80" : "w-16"
          }`}
        >
          <DashboardSidebar
            isOpen={isSidebarOpen}
            onToggle={() => setIsSidebarOpen((open) => !open)}
          />
        </aside>

        {/* Main Content Area - Flexible, scrollable */}
        <main className="flex-1 overflow-y-auto bg-gray-50 no-scrollbar">
          {children}
        </main>
      </div>
    </div>
  );
}
