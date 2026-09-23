"use client";

import { useState, type ReactNode } from "react";

type CollapsibleSectionProps = {
  title: string;
  summary?: string;
  defaultOpen?: boolean;
  children: ReactNode;
};

/** Disclosure wrapper for a page section -- same expand/collapse pattern as
 * LeaderboardExpander (chevron button header, content only mounted while
 * open), generalized for section titles rather than one metric row. Used to
 * let heavy sections (player lists, KPI/trend/forecast results) fold away
 * instead of always consuming vertical space. */
export function CollapsibleSection({ title, summary, defaultOpen = true, children }: CollapsibleSectionProps) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <div>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center justify-between gap-sm text-left"
      >
        <span className="flex flex-wrap items-baseline gap-sm">
          <span className="text-heading-5 text-ink-deep">{title}</span>
          {summary && <span className="text-body-sm text-stone">{summary}</span>}
        </span>
        <span
          className="text-steel transition-transform duration-(--duration-xs) ease-(--ease-primary)"
          style={{ transform: open ? "rotate(0deg)" : "rotate(-90deg)" }}
        >
          ▾
        </span>
      </button>
      {open && <div className="mt-md">{children}</div>}
    </div>
  );
}
