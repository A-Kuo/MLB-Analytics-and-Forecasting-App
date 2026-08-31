SELECT
    team_id,
    season,
    metric,
    forecast_year,
    predicted_value,
    lower_bound,
    upper_bound,
    model_name,
    created_at
FROM team_forecasts
WHERE team_id = %s
  AND season = %s
  AND metric = %s
ORDER BY forecast_year ASC;

/*

As with upsert, this only works if forecasts inserted

*/