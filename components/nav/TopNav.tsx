"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV_LINKS = [
  { href: "/insights", label: "Insights" },
  { href: "/analytics", label: "Analytics & Forecasts" },
];

type TopNavProps = {
  onToggleNews: () => void;
};

export function TopNav({ onToggleNews }: TopNavProps) {
  const pathname = usePathname();

  return (
    <header className="sticky top-0 z-50 border-b border-gray-800 bg-[#121212]">
      <div className="mx-auto flex h-16 w-full max-w-[1280px] items-center justify-between px-6">
        <div className="flex items-center gap-8">
          <Link href="/insights" className="text-xl font-bold text-white flex items-center gap-2">
            <span className="text-[#e31837]">MLB</span> Analytics
          </Link>
          <nav className="flex items-center gap-6">
            {NAV_LINKS.map((link) => {
              const active = pathname?.startsWith(link.href);
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  className={
                    active
                      ? "text-sm font-medium text-white border-b-2 border-[#e31837] py-5"
                      : "text-sm font-medium text-gray-400 hover:text-white py-5 transition-colors"
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
          onClick={onToggleNews}
          className="text-sm font-medium rounded-md border border-gray-700 hover:bg-gray-800 px-4 py-2 text-white transition-colors"
        >
          News Feed
        </button>
      </div>
    </header>
  );
}
