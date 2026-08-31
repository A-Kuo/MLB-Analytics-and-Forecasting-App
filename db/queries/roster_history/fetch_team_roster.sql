SELECT
    p.id,
    p.name,
    p.debut_year,
    p.last_active_year,
    p.active,
    rs.positions,
    rs.is_pitcher
FROM roster_stints AS rs
JOIN players AS p
    ON p.id = rs.player_id
WHERE rs.team_id = %s
ORDER BY
    p.active DESC,
    p.name ASC;