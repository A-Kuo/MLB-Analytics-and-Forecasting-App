import { NextResponse } from "next/server";

// Live scoreboard data -- unlike teams/news/insights, this is transient
// game-state (score, inning, outs, runners) that has no business living in
// the Neon data mart. Hit the public MLB Stats API directly, the same
// endpoint/hydrate combination as macroservice/teams.py's get_schedule.
const STATS_API_BASE = "https://statsapi.mlb.com/api/v1";
const LOOKAHEAD_DAYS = 7;

export type ScheduleGame = {
  gamePk: number;
  status: "preview" | "live" | "final";
  gameDate: string;
  awayTeamId: number;
  homeTeamId: number;
  awayScore: number;
  homeScore: number;
  inningNumber: number | null;
  inningHalf: "top" | "bottom" | null;
  outs: number;
  runners: { first: boolean; second: boolean; third: boolean };
};

function mapStatus(abstractGameState: string): ScheduleGame["status"] {
  if (abstractGameState === "Live") return "live";
  if (abstractGameState === "Final") return "final";
  return "preview";
}

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  // MLB's schedule day is Eastern time; UTC would roll to "tomorrow" every evening.
  const startDate =
    searchParams.get("date") ?? new Date().toLocaleDateString("en-CA", { timeZone: "America/New_York" });

  try {
    // No gameType filter: postseason games count. When the requested day has
    // none (off day, offseason), look ahead for the next day that does so the
    // strip shows upcoming games instead of disappearing.
    let date = startDate;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    let rawGames: any[] = [];
    for (let offset = 0; offset <= LOOKAHEAD_DAYS && rawGames.length === 0; offset++) {
      const d = new Date(`${startDate}T12:00:00Z`);
      d.setUTCDate(d.getUTCDate() + offset);
      date = d.toISOString().slice(0, 10);
      const res = await fetch(`${STATS_API_BASE}/schedule?sportId=1&hydrate=linescore,team&date=${date}`, {
        next: { revalidate: 30 },
      });
      if (!res.ok) throw new Error(`MLB Stats API responded ${res.status}`);
      const payload = await res.json();
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      rawGames = (payload.dates ?? []).flatMap((day: any) => day.games ?? []);
    }

    const games: ScheduleGame[] = rawGames.map((g) => {
      const linescore = g.linescore ?? {};
      const offense = linescore.offense ?? {};
      const inningState: string | undefined = linescore.inningState;
      return {
        gamePk: g.gamePk,
        status: mapStatus(g.status?.abstractGameState),
        gameDate: g.gameDate,
        awayTeamId: g.teams?.away?.team?.id,
        homeTeamId: g.teams?.home?.team?.id,
        awayScore: g.teams?.away?.score ?? 0,
        homeScore: g.teams?.home?.score ?? 0,
        inningNumber: linescore.currentInning ?? null,
        inningHalf: inningState === "Top" ? "top" : inningState === "Bottom" ? "bottom" : null,
        outs: linescore.outs ?? 0,
        runners: {
          first: Boolean(offense.first),
          second: Boolean(offense.second),
          third: Boolean(offense.third),
        },
      };
    });

    return NextResponse.json({ data: games, date }, { status: 200 });
  } catch {
    return NextResponse.json({ error: "Failed to fetch schedule" }, { status: 500 });
  }
}
