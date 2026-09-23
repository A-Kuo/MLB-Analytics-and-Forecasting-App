"use client";

import Image from "next/image";
import { useEffect, useRef, useState } from "react";

import { getSchedule, getTeams, type ScheduleGame, type Team } from "@/lib/api";

const SCROLL_STEP_PX = 400;
const REFRESH_INTERVAL_MS = 30_000;

type Base = "first" | "second" | "third";

/** Mini rotated-diamond runner graphic -- three 45deg squares positioned
 * like 1st/2nd/3rd base, filled when occupied. */
function RunnerDiamond({ runners }: { runners: ScheduleGame["runners"] }) {
  const baseClass = (occupied: boolean) =>
    `absolute h-1.5 w-1.5 rotate-45 border ${
      occupied ? "border-accent-blue bg-accent-blue" : "border-hairline-strong bg-transparent"
    }`;
  const bases: { key: Base; className: string }[] = [
    { key: "second", className: "top-0 left-1/2 -translate-x-1/2" },
    { key: "third", className: "left-0 top-1/2 -translate-y-1/2" },
    { key: "first", className: "right-0 top-1/2 -translate-y-1/2" },
  ];
  return (
    <div className="relative h-5 w-5">
      {bases.map(({ key, className }) => (
        <div key={key} className={`${baseClass(runners[key])} ${className}`} />
      ))}
    </div>
  );
}

function OutDots({ outs }: { outs: number }) {
  return (
    <div className="mt-0.5 flex gap-0.5">
      {[0, 1].map((i) => (
        <div key={i} className={`h-1.5 w-1.5 rounded-full ${outs > i ? "bg-accent-blue" : "bg-hairline-strong"}`} />
      ))}
    </div>
  );
}

function TeamRow({ team, score, highlight }: { team: Team | undefined; score: number; highlight: boolean }) {
  return (
    <div className="flex items-center justify-between gap-1.5">
      <div className="flex items-center gap-1.5 overflow-hidden">
        {team && <Image src={team.logo_url} alt="" width={14} height={14} unoptimized />}
        <span className="truncate text-micro font-semibold text-ink-deep">{team?.abbreviation ?? "--"}</span>
      </div>
      <span className={`font-mono text-body-sm-medium ${highlight ? "text-accent-blue" : "text-ink-deep"}`}>
        {score}
      </span>
    </div>
  );
}

function GameCell({ game, teamById }: { game: ScheduleGame; teamById: Map<number, Team> }) {
  const away = teamById.get(game.awayTeamId);
  const home = teamById.get(game.homeTeamId);
  const isLive = game.status === "live";
  const isFinal = game.status === "final";

  return (
    <div className="flex h-full w-44 flex-none items-center justify-between gap-2 border-r border-hairline px-3 transition-colors duration-(--duration-xs) ease-(--ease-primary) hover:bg-surface-soft">
      <div className="flex w-[62%] flex-col justify-center gap-0.5">
        <TeamRow team={away} score={game.awayScore} highlight={isLive && game.awayScore > game.homeScore} />
        <TeamRow team={home} score={game.homeScore} highlight={isLive && game.homeScore > game.awayScore} />
      </div>

      <div className="flex w-[35%] flex-col items-center justify-center">
        {isLive ? (
          <>
            <RunnerDiamond runners={game.runners} />
            <span className="mt-0.5 flex items-center gap-0.5 text-micro font-semibold text-steel">
              {game.inningHalf === "top" ? "▲" : "▼"}
              {game.inningNumber ?? ""}
            </span>
            <OutDots outs={game.outs} />
          </>
        ) : isFinal ? (
          <span className="text-micro font-semibold text-steel">Final</span>
        ) : (
          <span className="text-micro font-semibold text-steel">
            {new Date(game.gameDate).toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" })}
          </span>
        )}
      </div>
    </div>
  );
}

/** Low-profile, horizontally-scrolling live scoreboard strip -- the
 * Statcast/Baseball Savant gameday header analogue. Sits below TopNav so
 * every page shares one always-visible view of today's games; refreshes on
 * an interval rather than on user action since scores/outs/innings change
 * on their own. */
export function LiveScoreboard() {
  const [teams, setTeams] = useState<Team[]>([]);
  const [games, setGames] = useState<ScheduleGame[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    getTeams()
      .then(setTeams)
      .catch(() => {
        /* team logos/abbreviations degrade to placeholders if this fails */
      });
  }, []);

  useEffect(() => {
    let cancelled = false;
    function load() {
      getSchedule()
        .then((data) => !cancelled && setGames(data))
        .catch((err: Error) => !cancelled && setError(err.message));
    }
    load();
    const interval = setInterval(load, REFRESH_INTERVAL_MS);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  const teamById = new Map(teams.map((t) => [t.id, t]));
  const dateLabel = new Date().toLocaleDateString(undefined, { month: "numeric", day: "numeric" });

  if (error || (games && games.length === 0)) return null;

  return (
    <div className="flex h-14 w-full select-none items-center border-b border-hairline bg-canvas text-xs">
      <div className="flex h-full flex-none items-center border-r border-hairline px-4 text-body-sm-medium text-ink-deep">
        {dateLabel}
      </div>

      <div ref={scrollRef} className="no-scrollbar flex h-full flex-1 overflow-x-auto">
        {games === null ? (
          <div className="flex items-center px-4 text-micro text-steel">Loading today&apos;s games…</div>
        ) : (
          games.map((game) => <GameCell key={game.gamePk} game={game} teamById={teamById} />)
        )}
      </div>

      <div className="flex h-full flex-none items-center gap-1 border-l border-hairline px-2">
        <button
          type="button"
          aria-label="Scroll games left"
          onClick={() => scrollRef.current?.scrollBy({ left: -SCROLL_STEP_PX, behavior: "smooth" })}
          className="rounded-full p-1.5 text-steel transition-colors duration-(--duration-xs) ease-(--ease-primary) hover:bg-surface-soft hover:text-ink-deep"
        >
          ‹
        </button>
        <button
          type="button"
          aria-label="Scroll games right"
          onClick={() => scrollRef.current?.scrollBy({ left: SCROLL_STEP_PX, behavior: "smooth" })}
          className="rounded-full p-1.5 text-steel transition-colors duration-(--duration-xs) ease-(--ease-primary) hover:bg-surface-soft hover:text-ink-deep"
        >
          ›
        </button>
      </div>
    </div>
  );
}
