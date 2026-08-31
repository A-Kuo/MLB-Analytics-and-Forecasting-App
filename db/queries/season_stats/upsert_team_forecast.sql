/*
Relies on persistent forecasts.
Only add if implemented with
*/

INSERT INTO team_forecasts (
    team_id,
    season,
    metric,
    forecast_year,
    predicted_value,
    lower_bound,
    upper_bound,
    model_name,
    created_at
)
VALUES (
    %(team_id)s,
    %(season)s,
    %(metric)s,
    %(forecast_year)s,
    %(predicted_value)s,
    %(lower_bound)s,
    %(upper_bound)s,
    %(model_name)s,
    NOW()
)
ON CONFLICT (team_id, season, metric, forecast_year)
DO UPDATE SET
    predicted_value = EXCLUDED.predicted_value,
    lower_bound = EXCLUDED.lower_bound,
    upper_bound = EXCLUDED.upper_bound,
    model_name = EXCLUDED.model_name,
    created_at = NOW();