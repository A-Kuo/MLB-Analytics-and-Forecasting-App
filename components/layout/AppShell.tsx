"use client";

import { useState } from "react";
import { TopNav } from "@/components/nav/TopNav";
import { NewsDrawer } from "./NewsDrawer";

type AppShellProps = {
  children: React.ReactNode;
};

export function AppShell({ children }: AppShellProps) {
  const [newsOpen, setNewsOpen] = useState(false);
  // Ideally, selectedTeamIds would come from a global store, context, or URL params.
  // For now, we'll initialize it empty and let page components update it via some mechanism,
  // or parse it from the URL. Since this is a client component, we could use useSearchParams.
  
  return (
    <div className="flex min-h-screen flex-col bg-[#121212]">
      <TopNav onToggleNews={() => setNewsOpen(!newsOpen)} />
      <main className="flex-1">
        {children}
      </main>
      
      {/* We will pass selectedTeamIds when we have a way to extract them from URL.
          For the first pass, we can use an empty array. */}
      <NewsDrawer 
        selectedTeamIds={[]} 
        open={newsOpen} 
        onOpenChange={setNewsOpen} 
      />
    </div>
  );
}
