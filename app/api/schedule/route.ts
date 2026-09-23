import { NextResponse } from "next/server";

// Live scoreboard data -- unlike teams/news/insights, this is transient
// game-state (score, inning, outs, runners) that has no business living in
// the Neon data mart. Hit the public MLB Stats API directly, the same
// endpoint/hydrate combination as macroservice/teams.py's get_schedule.
const STATS_API_BASE = "https://statsapi.mlb.com/api/v1";

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
  const date = searchParams.get("date") ?? new Date().toISOString().slice(0, 10);

  try {
    const res = await fetch(
      `${STATS_API_BASE}/schedule?sportId=1&gameType=R&hydrate=linescore,team&date=${date}`,
      { next: { revalidate: 30 } },
    );
    if (!res.ok) throw new Error(`MLB Stats API responded ${res.status}`);
    const payload = await res.json();

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const rawGames: any[] = (payload.dates ?? []).flatMap((d: any) => d.games ?? []);

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
