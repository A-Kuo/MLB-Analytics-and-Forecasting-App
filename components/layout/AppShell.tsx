"use client";

import { useState } from "react";
import { TopNav } from "@/components/nav/TopNav";
import { NewsTeamIdsProvider, useNewsTeamIds } from "@/lib/newsContext";
import { NewsDrawer } from "./NewsDrawer";

type AppShellProps = {
  children: React.ReactNode;
};

function AppShellInner({ children }: AppShellProps) {
  const [newsOpen, setNewsOpen] = useState(false);
  const { teamIds } = useNewsTeamIds();

  return (
    <div className="min-h-screen bg-canvas">
      {/* Reserves the drawer's width (max-w-96) on md+ so the open feed sits
          beside the page instead of covering it. */}
      <div
        className={`flex min-h-screen flex-col transition-[padding] duration-(--duration-md) ease-(--ease-primary) ${
          newsOpen ? "md:pr-96" : ""
        }`}
      >
        <TopNav onToggleNews={() => setNewsOpen(!newsOpen)} />
        <main className="flex-1">
          {children}
        </main>
      </div>
      <NewsDrawer
        selectedTeamIds={teamIds}
        open={newsOpen}
        onOpenChange={setNewsOpen}
      />
    </div>
  );
}

export function AppShell({ children }: AppShellProps) {
  return (
    <NewsTeamIdsProvider>
      <AppShellInner>{children}</AppShellInner>
    </NewsTeamIdsProvider>
  );
}
