# MLB Data Service

A REST API in front of the MLB Stats API, Baseball Savant (Statcast), and MLB news RSS. Consuming applications call this service instead of hitting those upstreams directly, so ingestion concerns (rate limits, retries, response shape) live in one place rather than being duplicated across every consumer.

---

## Why a separate service

Data ingestion here is bursty and occasionally rate-limited: Statcast pulls can be large, MLB Stats API calls happen on every team/season/player change, and both are outside our control if they throttle or return transient errors. Putting that behind its own REST API keeps that concern independent of any particular consuming application's request/response cycle, and gives every caller the same retry behavior for free instead of re-implementing it.

---

## Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Liveness check |
| GET | `/teams` | All 30 MLB teams (id, name, colors, logo URL, news keywords) |
| GET | `/teams/{team_id}/roster?season=` | Active roster for a team/season |
| GET | `/teams/{team_id}/schedule?season=` | Completed games with linescores for a team/season |
| GET | `/players/{player_id}/game-log?season=&group=hitting\|pitching` | Per-game stat splits |
| GET | `/players/{player_id}/season-stats?season=&group=hitting\|pitching` | Cumulative season stat line |
| GET | `/statcast/pitcher/{player_id}?season=` | Every pitch thrown by this pitcher, from Baseball Savant |
| GET | `/statcast/batter/{player_id}?season=` | Every batted-ball event for this hitter, from Baseball Savant |
| GET | `/news?keywords=Yankees&keywords=New+York+Yankees&limit=10` | Headlines matching any of the given keywords |

Interactive API docs are available at `/docs` (Swagger UI) once the service is running.

---

## Exponential backoff

Every outbound call to an upstream (MLB Stats API, Baseball Savant, NewsAPI) goes through `backoff.py`'s `request_with_backoff`, which:

- Retries HTTP 429, 5xx responses, and connection/timeout errors
- Uses full-jitter exponential backoff (`random.uniform(0, min(cap, base * 2^attempt))`) between attempts
- Honors an upstream `Retry-After` header when present, instead of guessing
- Fails fast (no retry) on other 4xx responses, since those won't succeed on a retry
- Raises `UpstreamError` once `max_retries` is exhausted, so callers get a clear failure rather than a silent empty response

---

## Running locally

```bash
cd data_service
python -m venv .venv && source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt

# Optional: add a NewsAPI key -- without it, /news falls back to MLB.com's public RSS feed
cp .env.example .env

uvicorn main:app --reload --port 8000
```

Run the test suite:

```bash
pip install -r requirements-dev.txt
pytest
```

## Running with Docker

```bash
docker build -t mlb-data-service .
docker run -p 8000:8000 --env-file .env mlb-data-service
```

---

## Notes

- Baseball Savant's CSV search endpoint is unofficial and undocumented; it is confirmed working as of this writing but has no stability guarantee from MLB. Statcast endpoints can return an empty list for a player/season with no recorded pitches or batted balls -- that is a valid response, not an error.
- `config/teams.json` is a local copy of the dashboard's team metadata, kept here so this service has no file-path dependency on any other part of the repository.
- No caching layer is included yet; each request re-fetches from the upstream. Add one at the call site if a consumer's access pattern warrants it.
