"use client";

import { createContext, useContext, useState, type ReactNode } from "react";

/**
 * Shared "which teams is News Feed scoped to" state -- the equivalent of
 * Streamlit's st.session_state["news_context"] (see app.py's comment on
 * why News Feed is shared/rendered once across pages there). AppShell
 * renders NewsDrawer once at the layout level, outside either page, so
 * whichever page last touched team selection needs a way to hand its
 * team ids up to it; a page calls useNewsTeamIds()'s setter whenever its
 * own selection changes, and AppShell reads the same context to pass into
 * NewsDrawer.
 */
const NewsTeamIdsContext = createContext<{
  teamIds: number[];
  setTeamIds: (ids: number[]) => void;
} | null>(null);

export function NewsTeamIdsProvider({ children }: { children: ReactNode }) {
  const [teamIds, setTeamIds] = useState<number[]>([]);
  return (
    <NewsTeamIdsContext.Provider value={{ teamIds, setTeamIds }}>{children}</NewsTeamIdsContext.Provider>
  );
}

export function useNewsTeamIds() {
  const ctx = useContext(NewsTeamIdsContext);
  if (!ctx) throw new Error("useNewsTeamIds must be used within NewsTeamIdsProvider");
  return ctx;
}
