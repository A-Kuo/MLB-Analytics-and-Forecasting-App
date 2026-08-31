import { neon } from "@neondatabase/serverless";

const databaseUrl = process.env.DATABASE_URL;

if (!databaseUrl) {
  throw new Error("DATABASE_URL is not configured.");
}

export const sql = neon(databaseUrl);


/* 

allows for server side route:

import { sql } from "@/lib/db/client";

export async function getTeamNews(teamIds: number[], days: number, limit: number) {
  return sql`
    SELECT
      team_id,
      source,
      priority,
      headline,
      thumbnail,
      link,
      published_at
    FROM team_news
    WHERE team_id = ANY(${teamIds})
      AND published_at >= NOW() - make_interval(days => ${days})
    ORDER BY published_at DESC, priority ASC
    LIMIT ${limit};
  `;
}

*/