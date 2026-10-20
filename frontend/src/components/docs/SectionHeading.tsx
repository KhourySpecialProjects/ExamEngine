"use client";

import {
  type SidebarComponents,
  SidebarSeparator,
} from "fumadocs-ui/components/layout/sidebar";

/**
 * A docs sidebar section heading on its own line. Fumadocs' default is
 * inline, so two sections with no pages between them share a line.
 */
export const SectionHeading: SidebarComponents["Separator"] = ({ item }) => (
  <SidebarSeparator className="flex [&:not(:first-child)]:mt-6">
    {item.icon}
    {item.name}
  </SidebarSeparator>
);
