"use client";

import { Onborda, OnbordaProvider } from "onborda";
import { useState } from "react";
import { DashboardHeader } from "@/components/layouts/DashboardHeader";
import { DashboardSidebar } from "@/components/layouts/DashboardSidebar";
import { TourCard } from "@/components/tour";
import { steps } from "@/components/tour/steps";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);

  return (
    <OnbordaProvider>
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
        <Onborda
          steps={steps}
          cardComponent={TourCard}
          shadowOpacity="0.8"
          cardTransition={{ type: "spring", stiffness: 100, damping: 10 }}
        >
          {/** biome-ignore lint/complexity/noUselessFragments: this is important for linting */}
          <></>
        </Onborda>
      </div>
    </OnbordaProvider>
  );
}
