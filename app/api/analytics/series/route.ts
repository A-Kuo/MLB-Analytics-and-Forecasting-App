import { NextResponse } from "next/server";
import { getAggregateSeries } from "@/lib/db/analytics";

export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    const playerIdsParam = searchParams.get("playerIds");
    const metric = searchParams.get("metric");
    const group = searchParams.get("group");
    const startYearStr = searchParams.get("startYear");
    const endYearStr = searchParams.get("endYear");

    if (!playerIdsParam || !metric || !group || !startYearStr || !endYearStr) {
      return NextResponse.json(
        { error: "Missing required parameters: playerIds, metric, group, startYear, endYear" },
        { status: 400 },
      );
    }
    if (group !== "hitting" && group !== "pitching") {
      return NextResponse.json({ error: "group must be 'hitting' or 'pitching'" }, { status: 400 });
    }

    const playerIds = playerIdsParam.split(",").map((id) => parseInt(id, 10)).filter((id) => !isNaN(id));
    const startYear = parseInt(startYearStr, 10);
    const endYear = parseInt(endYearStr, 10);
    if (isNaN(startYear) || isNaN(endYear) || playerIds.length === 0) {
      return NextResponse.json({ error: "Invalid parameters" }, { status: 400 });
    }

    const series = await getAggregateSeries(playerIds, metric, group, startYear, endYear);
    return NextResponse.json({ data: series }, { status: 200 });
  } catch (error) {
    console.error("Aggregate series fetch error:", error);
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Failed to fetch aggregate series" },
      { status: 500 },
    );
  }
}
