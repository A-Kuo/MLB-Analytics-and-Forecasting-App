INSERT INTO players (
    id,
    name,
    debut_year,
    last_active_year,
    active
)
VALUES (
    %(id)s,
    %(name)s,
    %(debut_year)s,
    %(last_active_year)s,
    %(active)s
)
ON CONFLICT (id)
DO UPDATE SET
    name = EXCLUDED.name,
    debut_year = EXCLUDED.debut_year,
    last_active_year = EXCLUDED.last_active_year,
    active = EXCLUDED.active;