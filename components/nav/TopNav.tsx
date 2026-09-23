"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";

// Insights first, matching the Streamlit app's nav order. The wordmark
// (below) links to app/page.tsx's project-overview home page; these two
// tabs are the actual product pages.
const NAV_LINKS = [
  { href: "/insights", label: "Insights" },
  { href: "/analytics", label: "Analytics and Forecasts" },
];

const MLB_LOGO_URL = "https://www.mlbstatic.com/team-logos/league-on-dark/1.svg";
const GITHUB_REPO_URL = "https://github.com/A-Kuo/MLB-Analytics-and-Forecasting-App";

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
          <Link href="/" className="flex items-center gap-2 text-xl font-bold text-ink-deep">
            <Image src={MLB_LOGO_URL} alt="MLB" width={32} height={32} unoptimized />
            MLB Analytics &amp; Forecasting
          </Link>
          <a
            href={GITHUB_REPO_URL}
            target="_blank"
            rel="noopener noreferrer"
            aria-label="View source on GitHub"
            className="ml-auto rounded-full p-2 text-steel transition-colors duration-(--duration-sm) ease-(--ease-primary) hover:bg-surface-soft hover:text-ink-deep"
          >
            <svg viewBox="0 0 24 24" width="22" height="22" fill="currentColor" aria-hidden="true">
              <path d="M12 .5C5.65.5.5 5.65.5 12c0 5.09 3.29 9.4 7.86 10.93.57.1.79-.25.79-.55 0-.27-.01-1.17-.02-2.12-3.2.7-3.88-1.36-3.88-1.36-.52-1.34-1.28-1.69-1.28-1.69-1.04-.72.08-.7.08-.7 1.16.08 1.77 1.19 1.77 1.19 1.03 1.77 2.7 1.26 3.36.96.1-.74.4-1.26.72-1.55-2.55-.29-5.23-1.28-5.23-5.68 0-1.26.45-2.28 1.19-3.09-.12-.29-.51-1.46.11-3.04 0 0 .97-.31 3.18 1.18a11.1 11.1 0 0 1 2.9-.39c.98 0 1.97.13 2.9.39 2.2-1.49 3.17-1.18 3.17-1.18.63 1.58.24 2.75.12 3.04.74.81 1.19 1.83 1.19 3.09 0 4.41-2.69 5.39-5.25 5.67.41.36.78 1.06.78 2.15 0 1.55-.01 2.8-.01 3.18 0 .31.21.66.79.55C20.21 21.39 23.5 17.08 23.5 12 23.5 5.65 18.35.5 12 .5Z" />
            </svg>
          </a>
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
                      ? "border-b-2 border-accent-blue py-4 text-sm font-medium text-ink-deep"
                      : "py-4 text-sm font-medium text-steel transition-colors duration-(--duration-sm) ease-(--ease-primary) hover:text-ink-deep"
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
            className="rounded-full border border-hairline-strong px-4 py-2 text-sm font-medium text-ink transition-colors duration-(--duration-sm) ease-(--ease-primary) hover:bg-surface-soft"
          >
            News Feed
          </button>
        </div>
      </div>
    </header>
  );
}
