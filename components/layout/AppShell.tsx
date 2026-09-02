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
    <div className="flex min-h-screen flex-col bg-canvas">
      <TopNav onToggleNews={() => setNewsOpen(!newsOpen)} />
      <main className="flex-1">
        {children}
      </main>
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
