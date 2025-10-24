"use client";

// biome-ignore lint/suspicious/noShadowRestrictedNames: false postive
import { LayoutGrid, List, Map } from "lucide-react";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";

type ViewType = "density" | "compact" | "list";

interface ViewTabSwitcherProps {
  activeView: ViewType;
  onViewChange: (view: ViewType) => void;
}

export function ViewTabSwitcher({
  activeView,
  onViewChange,
}: ViewTabSwitcherProps) {
  return (
    <Tabs value={activeView} onValueChange={(v) => onViewChange(v as ViewType)}>
      <TabsList className="border border-gray-300 !p-1">
        <TabsTrigger
          value="density"
          className="gap-2 data-[state=active]:bg-black data-[state=active]:text-white transition-all duration-300"
        >
          <Map className="h-4 w-4" />
          Density
        </TabsTrigger>
        <TabsTrigger
          value="compact"
          className="gap-2 data-[state=active]:bg-black data-[state=active]:text-white transition-all duration-300"
        >
          <LayoutGrid className="h-4 w-4" />
          Compact
        </TabsTrigger>
        <TabsTrigger
          value="list"
          className="gap-2 data-[state=active]:bg-black data-[state=active]:text-white transition-all duration-300"
        >
          <List className="h-4 w-4" />
          List
        </TabsTrigger>
      </TabsList>
    </Tabs>
  );
}
