import { DocsLayout } from "fumadocs-ui/layouts/docs";
import { RootProvider } from "fumadocs-ui/provider";
import { LayoutDashboard } from "lucide-react";
import type { Metadata } from "next";
import Image from "next/image";
import { source } from "@/lib/docs/source";

export const metadata: Metadata = {
  title: {
    template: "%s | ExamEngine Docs",
    default: "ExamEngine Docs",
  },
  description: "How to use ExamEngine to schedule final exams.",
};

export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    // The app is light-only, so the docs are too: no theme provider or switch.
    // Search uses a static index built from the pages (see search.json).
    <RootProvider
      theme={{ enabled: false }}
      search={{ options: { type: "static", api: "/docs/search.json" } }}
    >
      <DocsLayout
        tree={source.pageTree}
        nav={{
          title: (
            <Image src="/logo.svg" alt="ExamEngine" width={152} height={16} />
          ),
          url: "/docs",
        }}
        links={[
          {
            text: "Back to ExamEngine",
            url: "/dashboard",
            icon: <LayoutDashboard />,
          },
        ]}
        themeSwitch={{ enabled: false }}
      >
        {children}
      </DocsLayout>
    </RootProvider>
  );
}
