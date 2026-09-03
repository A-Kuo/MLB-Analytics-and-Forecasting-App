INSERT INTO players (
    id,
    name,
    debut_year,
    last_active_year,
    active
)
VALUES (
    :id,
    :name,
    :debut_year,
    :last_active_year,
    :active
)
ON CONFLICT (id)
DO UPDATE SET
    name = EXCLUDED.name,
    debut_year = EXCLUDED.debut_year,
    last_active_year = EXCLUDED.last_active_year,
    active = EXCLUDED.active;
