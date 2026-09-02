import { NextResponse } from "next/server";
import { getTeamRosterWithActiveYears } from "@/lib/db/roster";

export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    const teamIdStr = searchParams.get("teamId");
    if (!teamIdStr) {
      return NextResponse.json({ error: "Missing required parameter: teamId" }, { status: 400 });
    }
    const teamId = parseInt(teamIdStr, 10);
    if (isNaN(teamId)) {
      return NextResponse.json({ error: "Invalid teamId" }, { status: 400 });
    }

    const roster = await getTeamRosterWithActiveYears(teamId);
    return NextResponse.json({ data: roster }, { status: 200 });
  } catch (error) {
    console.error("Roster fetch error:", error);
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Failed to fetch roster" },
      { status: 500 },
    );
  }
}
