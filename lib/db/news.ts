import { query } from "./client";

export async function getTeamNews(teamIds: number[], limit = 10, days = 7) {
  if (!teamIds || teamIds.length === 0) {
    return [];
  }

  const result = await query(
    `
    SELECT team_id, source, headline, thumbnail, link as url, published_at
    FROM team_news
    WHERE team_id = ANY($1) AND published_at >= now() - make_interval(days => $2)
    ORDER BY priority ASC, published_at DESC
    LIMIT $3
    `,
    [teamIds, days, limit]
  );

  return result.rows;
}
