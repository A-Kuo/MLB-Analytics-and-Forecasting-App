"use client";

import { useEffect, useState } from "react";

import { GENERAL_NEWS_HUB_URL, getTeamNews, getTeams, teamNewsHubUrl, type NewsItem, type Team } from "@/lib/api";

type NewsDrawerProps = {
  selectedTeamIds: number[];
  open: boolean;
  onOpenChange: (open: boolean) => void;
};

// Alphabetical-by-name cap, matching utils/constants.MAX_NEWS_TEAMS -- bounds
// worst-case query size when Insights' "All Teams" default is still selected.
const MAX_NEWS_TEAMS = 10;
const NEWS_LOOKBACK_DAYS = 7;

export function NewsDrawer({ selectedTeamIds, open, onOpenChange }: NewsDrawerProps) {
  const [teams, setTeams] = useState<Team[]>([]);
  const [news, setNews] = useState<NewsItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open || teams.length > 0) return;
    getTeams()
      .then(setTeams)
      .catch(() => {
        /* team names/hub links degrade gracefully to nothing if this fails */
      });
  }, [open, teams.length]);

  const teamById = new Map(teams.map((t) => [t.id, t]));
  const cappedTeamIds = [...selectedTeamIds]
    .sort((a, b) => (teamById.get(a)?.name ?? "").localeCompare(teamById.get(b)?.name ?? ""))
    .slice(0, MAX_NEWS_TEAMS);

  useEffect(() => {
    if (!open) return;
    if (cappedTeamIds.length === 0) {
      setNews([]);
      return;
    }
    setLoading(true);
    setError(null);
    getTeamNews(cappedTeamIds, NEWS_LOOKBACK_DAYS)
      .then(setNews)
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
    // cappedTeamIds is derived fresh each render from selectedTeamIds + teams;
    // joining to a string keeps the effect from re-firing on referential
    // changes alone.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, cappedTeamIds.join(",")]);

  // Team hub links first, general MLB.com hub last -- matches app.py's
  // sidebar renderer exactly (one link per line, not a joined caption).
  const hubLinks: { url: string; label: string }[] = cappedTeamIds
    .map((id) => teamById.get(id))
    .filter((t): t is Team => Boolean(t))
    .map((t) => ({ url: teamNewsHubUrl(t.id), label: `${t.name} News` }));
  hubLinks.push({ url: GENERAL_NEWS_HUB_URL, label: "MLB News" });

  return (
    <>
      {open && (
        <div
          className="fixed inset-0 z-40 bg-black/50 transition-opacity md:hidden"
          onClick={() => onOpenChange(false)}
        />
      )}

      <div
        className={`fixed inset-y-0 right-0 z-50 w-full max-w-sm transform bg-surface shadow-xl transition-transform duration-(--duration-md) ease-(--ease-primary) ${
          open ? "translate-x-0" : "translate-x-full"
        }`}
      >
        <div className="flex h-full flex-col">
          <div className="flex items-center justify-between border-b border-hairline p-4">
            <h2 className="flex items-center gap-2 text-xl font-bold text-ink-deep">
              <span className="text-mlb-red">MLB</span> News Feed
            </h2>
            <button
              onClick={() => onOpenChange(false)}
              className="rounded-full p-2 text-steel transition-colors duration-(--duration-xs) ease-(--ease-primary) hover:bg-surface-soft hover:text-ink-deep"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="24"
                height="24"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <line x1="18" y1="6" x2="6" y2="18"></line>
                <line x1="6" y1="6" x2="18" y2="18"></line>
              </svg>
            </button>
          </div>

          {/* Headlines ABOVE the news hub links -- headlines are the more
              important content and get most of the drawer's height. */}
          <div className="flex-[3] overflow-y-auto p-4">
            <h3 className="mb-4 text-micro-uppercase text-steel">
              Headlines from the last {NEWS_LOOKBACK_DAYS} days
            </h3>

            {loading ? (
              <div aria-live="polite" className="space-y-4">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="animate-pulse space-y-2">
                    <div className="h-24 rounded bg-surface-soft"></div>
                    <div className="h-4 w-3/4 rounded bg-surface-soft"></div>
                  </div>
                ))}
              </div>
            ) : cappedTeamIds.length === 0 ? (
              <div className="py-8 text-center text-stone">
                <p>Select a team to see its news.</p>
              </div>
            ) : error ? (
              <div className="py-8 text-center text-semantic-error">
                <p>{error}</p>
              </div>
            ) : news.length === 0 ? (
              <div className="py-8 text-center text-stone">
                <p>No cached news for the selected teams yet. Run the ingestion workflow, or wait for the next scheduled run.</p>
              </div>
            ) : (
              <div className="space-y-3">
                {news.map((item) => (
                  // Thumbnail + headline together are one clickable card,
                  // matching utils/news_cards.news_card_html's structure --
                  // not a side-by-side layout with only the text clickable.
                  <a
                    key={item.id}
                    href={item.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="block rounded-md p-2 transition-colors duration-(--duration-xs) ease-(--ease-primary) hover:bg-mlb-link-hover/10"
                  >
                    {item.thumbnail_url && (
                      <img
                        src={item.thumbnail_url}
                        alt=""
                        loading="lazy"
                        className="mb-2 h-[120px] w-full rounded object-cover"
                      />
                    )}
                    <div className="text-body-sm-medium leading-snug text-ink">{item.headline}</div>
                    <div className="mt-1 flex items-center gap-2 text-micro text-stone">
                      <span className="truncate">{item.source}</span>
                      <span>·</span>
                      <span>{item.published_at ? new Date(item.published_at).toLocaleDateString() : ""}</span>
                    </div>
                  </a>
                ))}
              </div>
            )}
          </div>

          {/* News Hubs: scrollable, condensed spacing -- covers every
              selected team, not just the first. */}
          <div className="flex-1 border-t border-hairline p-4">
            <h3 className="mb-2 text-micro-uppercase text-steel">News Hubs</h3>
            <div className="max-h-[150px] space-y-0.5 overflow-y-auto">
              {hubLinks.map(({ url, label }) => (
                <a key={url} href={url} target="_blank" rel="noopener noreferrer" className="block text-body-sm">
                  {label}
                </a>
              ))}
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
