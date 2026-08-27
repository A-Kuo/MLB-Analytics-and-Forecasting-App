"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";

/**
 * Adapted from DESIGN.md's "Top Navigation (Marketing)" component -- the
 * one documented component that maps naturally onto a dashboard: sticky
 * white bar, app name left, this app's own two destinations in the link
 * slot (replacing Notion's Product/AI/Solutions links), and a News Feed
 * toggle right-aligned (replacing Notion's "Get Notion free" + "Log in"
 * slot). Fully replaces the Streamlit sidebar's job (page nav + News Feed
 * toggle) established earlier this session -- no sidebar in this rewrite.
 */
const NAV_LINKS = [
  { href: "/analytics", label: "Analytics and Forecasts" },
  { href: "/insights", label: "Insights" },
];

export function TopNav() {
  const pathname = usePathname();
  const [newsOpen, setNewsOpen] = useState(false);

  return (
    <header className="sticky top-0 z-50 border-b border-hairline bg-canvas">
      <div className="mx-auto flex h-16 max-w-[1280px] items-center justify-between px-xl">
        <div className="flex items-center gap-xxl">
          <Link href="/analytics" className="text-heading-5 text-ink">
            MLB Analytics
          </Link>
          <nav className="flex items-center gap-lg">
            {NAV_LINKS.map((link) => {
              const active = pathname?.startsWith(link.href);
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  className={
                    active
                      ? "text-body-sm-medium text-ink"
                      : "text-body-sm-medium text-steel"
                  }
                >
                  {link.label}
                </Link>
              );
            })}
          </nav>
        </div>
        <button
          type="button"
          onClick={() => setNewsOpen((open) => !open)}
          className="text-button-md rounded-md border border-hairline-strong px-md py-xs text-ink"
          aria-pressed={newsOpen}
        >
          News Feed
        </button>
      </div>
      {newsOpen ? (
        <div className="border-t border-hairline bg-surface px-xl py-md">
          <p className="text-body-sm text-steel">
            News Feed content ships in a later phase (currently ported from the Streamlit
            sidebar in a follow-up plan).
          </p>
        </div>
      ) : null}
    </header>
  );
}
