"use client";

import { useEffect, useState } from "react";

import { LeaderboardExpander } from "@/components/insights/LeaderboardExpander";
import { EARLIEST_SEASON, SeasonSelector } from "@/components/insights/SeasonSelector";
import { TeamSelector } from "@/components/insights/TeamSelector";
import { getTeams, type Team } from "@/lib/api";
import { HITTING_METRICS, PITCHING_METRICS } from "@/lib/metrics";
import { useNewsTeamIds } from "@/lib/newsContext";

const LEADERBOARD_LIMIT = 10;

export default function InsightsPage() {
  const [teams, setTeams] = useState<Team[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedTeamIds, setSelectedTeamIds] = useState<Set<number>>(new Set());
  // Defaults to last completed season, matching pages/insights.py
  // (current_year - 1), not the in-progress current season.
  const [season, setSeason] = useState<number>(new Date().getFullYear() - 1);
  const { setTeamIds } = useNewsTeamIds();

  useEffect(() => {
    getTeams()
      .then((fetched) => {
        setTeams(fetched);
        setSelectedTeamIds(new Set(fetched.map((t) => t.id))); // defaults to all teams selected
      })
      .catch((err: Error) => setError(err.message));
  }, []);

  // Hands the current team selection up to the shared News Feed drawer --
  // the Next.js equivalent of app.py's st.session_state["news_context"].
  useEffect(() => {
    setTeamIds([...selectedTeamIds]);
  }, [selectedTeamIds, setTeamIds]);

  return (
    <div className="mx-auto flex max-w-[1280px] flex-col gap-xl px-6 py-xl">
      <div>
        <h1 className="text-heading-1 text-ink-deep">Insights</h1>
        <p className="text-subtitle text-slate">Season leaderboards by metric, across the teams you select.</p>
      </div>

      {error ? (
        <p className="text-body-sm text-semantic-error">Failed to reach the API: {error}</p>
      ) : teams === null ? (
        <p className="text-body-sm text-steel">Loading teams…</p>
      ) : (
        <>
          <section>
            <h2 className="mb-md text-heading-5 text-ink-deep">Teams</h2>
            <TeamSelector teams={teams} selectedTeamIds={selectedTeamIds} onChange={setSelectedTeamIds} />
          </section>

          <section>
            <h2 className="mb-md text-heading-5 text-ink-deep">Season</h2>
            <SeasonSelector selectedSeason={season} onChange={setSeason} minYear={EARLIEST_SEASON} />
          </section>

          <section className="flex flex-col gap-lg">
            <h2 className="text-heading-5 text-ink-deep">Leaderboards</h2>

            <div>
              <h3 className="mb-sm text-heading-4 text-ink">Hitting</h3>
              <div className="flex flex-col gap-xs">
                {HITTING_METRICS.map(([key, acronym]) => (
                  <LeaderboardExpander
                    key={key}
                    metricKey={key}
                    acronym={acronym}
                    group="hitting"
                    season={season}
                    teamIds={[...selectedTeamIds]}
                    limit={LEADERBOARD_LIMIT}
                  />
                ))}
              </div>
            </div>

            <div>
              <h3 className="mb-sm text-heading-4 text-ink">Pitching</h3>
              <div className="flex flex-col gap-xs">
                {PITCHING_METRICS.map(([key, acronym]) => (
                  <LeaderboardExpander
                    key={key}
                    metricKey={key}
                    acronym={acronym}
                    group="pitching"
                    season={season}
                    teamIds={[...selectedTeamIds]}
                    limit={LEADERBOARD_LIMIT}
                  />
                ))}
              </div>
            </div>
          </section>
        </>
      )}
    </div>
  );
}
