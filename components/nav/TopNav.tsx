"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";

// Insights first, matching the Streamlit app's nav order (Insights is that
// app's home page too -- see app/page.tsx's redirect).
const NAV_LINKS = [
  { href: "/insights", label: "Insights" },
  { href: "/analytics", label: "Analytics and Forecasts" },
];

const MLB_LOGO_URL = "https://www.mlbstatic.com/team-logos/league-on-dark/1.svg";

type TopNavProps = {
  onToggleNews: () => void;
};

export function TopNav({ onToggleNews }: TopNavProps) {
  const pathname = usePathname();

  return (
    <header className="sticky top-0 z-50 border-b border-hairline bg-surface">
      <div className="mx-auto flex w-full max-w-[1280px] flex-col px-6">
        {/* Logo row -- above the tab selection below, not beside it */}
        <div className="flex h-16 items-center">
          <Link href="/insights" className="flex items-center gap-2 text-xl font-bold text-ink-deep">
            <Image src={MLB_LOGO_URL} alt="MLB" width={32} height={32} unoptimized />
            MLB Analytics Dashboard
          </Link>
        </div>
        {/* Tab row */}
        <div className="flex items-center justify-between border-t border-hairline">
          <nav className="flex items-center gap-6">
            {NAV_LINKS.map((link) => {
              const active = pathname?.startsWith(link.href);
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  className={
                    active
                      ? "border-b-2 border-mlb-red py-4 text-sm font-medium text-ink-deep"
                      : "py-4 text-sm font-medium text-steel transition-colors hover:text-ink-deep"
                  }
                >
                  {link.label}
                </Link>
              );
            })}
          </nav>
          <button
            type="button"
            onClick={onToggleNews}
            className="rounded-md border border-hairline-strong px-4 py-2 text-sm font-medium text-ink transition-colors hover:bg-surface-soft"
          >
            News Feed
          </button>
        </div>
      </div>
    </header>
  );
}
