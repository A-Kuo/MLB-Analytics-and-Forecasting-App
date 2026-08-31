import { NextResponse } from "next/server";
import { getTeamNews } from "@/lib/db/news";

export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    const teamIdsParam = searchParams.get("teamIds");
    
    let teamIds: number[] = [];
    if (teamIdsParam) {
      teamIds = teamIdsParam.split(",").map((id) => parseInt(id, 10)).filter((id) => !isNaN(id));
    }

    const limit = parseInt(searchParams.get("limit") || "10", 10);
    const days = parseInt(searchParams.get("days") || "7", 10);

    const news = await getTeamNews(teamIds, limit, days);
    
    // Convert thumbnail to thumbnail_url to match frontend expectations
    const formattedNews = news.map(item => ({
      ...item,
      thumbnail_url: item.thumbnail,
      id: item.url // Using url as ID since it's unique
    }));

    return NextResponse.json({ data: formattedNews }, { status: 200 });
  } catch (error) {
    console.error("News fetch error:", error);
    return NextResponse.json(
      { error: "Failed to fetch news" },
      { status: 500 }
    );
  }
}
