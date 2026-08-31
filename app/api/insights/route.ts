import { NextResponse } from "next/server";
import { getInsightsLeaderboard } from "@/lib/db/insights";

export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    const seasonStr = searchParams.get("season");
    const group = searchParams.get("group");
    const metric = searchParams.get("metric");
    const teamIdsParam = searchParams.get("teamIds");
    const limitStr = searchParams.get("limit");

    if (!seasonStr || !group || !metric || !teamIdsParam) {
      return NextResponse.json(
        { error: "Missing required parameters: season, group, metric, teamIds" },
        { status: 400 }
      );
    }

    const season = parseInt(seasonStr, 10);
    const teamIds = teamIdsParam.split(",").map((id) => parseInt(id, 10)).filter((id) => !isNaN(id));
    const limit = limitStr ? parseInt(limitStr, 10) : 10;

    if (isNaN(season) || teamIds.length === 0) {
      return NextResponse.json(
        { error: "Invalid parameters" },
        { status: 400 }
      );
    }

    const data = await getInsightsLeaderboard(metric, group, season, teamIds, limit);
    return NextResponse.json({ data }, { status: 200 });
  } catch (error) {
    console.error("Insights fetch error:", error);
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Failed to fetch insights" },
      { status: 500 }
    );
  }
}
