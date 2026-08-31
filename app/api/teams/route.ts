import { NextResponse } from "next/server";
import { getTeams } from "@/lib/db/teams";

export async function GET() {
  try {
    const teams = await getTeams();
    return NextResponse.json({ data: teams }, { status: 200 });
  } catch (error) {
    return NextResponse.json(
      { error: "Failed to fetch teams" },
      { status: 500 }
    );
  }
}
