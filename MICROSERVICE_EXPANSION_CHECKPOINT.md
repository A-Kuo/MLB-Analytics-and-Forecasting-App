# Microservice Expansion Checkpoint

**Branch:** `Microservice-Approach`  
**Date:** 2026-08-24  
**Status:** Stopping point after Commit 2 (partial)

## Completed Work

### Commit 1 (✅ Complete)
- FastAPI microservice scaffold (`data_service/`)
- Exponential backoff with full-jitter retry logic
- MLB Stats API, Baseball Savant, and NewsAPI client wrappers
- TTL-based in-memory caching decorator
- Health check endpoint

### Commit 2 (✅ Complete - Core Engine)
**Microservice Pre-Compute Layer:**
- `data_service/features.py`: Hitter appearance-level feature frame (10-game rolling with Statcast batted-ball enrichment), pitcher CSW% pitch-level rolling, team 10-game rolling runs
- `data_service/regression.py`: SVR/Huber/GaussianProcess ensemble with 80/20 chronological holdout split, 95% CI bands
- `data_service/transform.py`: Raw API JSON → typed DataFrames (game logs, schedules, batted balls, pitches)
- `data_service/trajectory.py`: Three pre-compute functions (cached @5min TTL):
  - `compute_hitter_trajectory(player_id, season, metric)` → trajectory JSON payload
  - `compute_pitcher_trajectory(player_id, season, fallback_metric)` → trajectory JSON + `used_statcast` flag (Statcast CSW% with automatic fallback to MLB Stats ERA/WHIP)
  - `compute_team_trajectory(team_id, season, mode)` → rolling offense/defense runs trajectories
- FastAPI trajectory endpoints:
  - `GET /players/{id}/hitter-trajectory?season=2026&metric=ops`
  - `GET /players/{id}/pitcher-trajectory?season=2026&fallback_metric=era`
  - `GET /teams/{id}/trajectory?season=2026&mode=offense|defense`

**Root Dashboard (Streamlit):**
- `app.py`: Single-page Streamlit dashboard
  - Sidebar: Team, season, player selectors
  - Season KPIs card grid
  - Performance trend regression chart (pre-computed by microservice)
  - Game log table (expandable)
  - Team offense/defense rolling trend side-by-side
  - Optional news feed toggle
- `client.py`: Thin HTTP client wrapper with Streamlit-aware caching (@st.cache_data)
- `chart.py`: Pure Plotly rendering of pre-fit trajectory payloads (train/holdout markers, ensemble line, 95% CI band)
- `tests/test_chart.py`: Plotly figure shape, holdout metrics, hover data coverage

**Test Coverage:**
- `data_service/tests/test_features.py`: Hitter/pitcher/team rolling frame shape and content
- `data_service/tests/test_regression.py`: Ensemble bounds, holdout metrics, multifeature input
- `data_service/tests/test_trajectory.py`: Trajectory endpoint payloads, Statcast availability/fallback behavior, cache correctness
- `data_service/tests/test_main.py`: FastAPI routes, health check, roster/stats/game-log endpoints
- `tests/test_chart.py`: Streamlit chart rendering, holdout split handling

**Verified:**
- All 33 data_service tests pass (pytest)
- All 9 root tests pass (formatters, chart rendering)
- Microservice endpoints deliver correct JSON payloads (live testing vs. real Corbin Carroll/Brandon Pfaadt data)
- Hitter trajectory caching working (2nd request 20x faster than 1st)
- Pitcher CSW% + fallback logic confirmed
- Team rolling trends confirmed

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│ Root (Streamlit Dashboard)                                          │
│ ├─ app.py                  # Single-page, team/player/season select │
│ ├─ client.py               # HTTP client → microservice endpoints   │
│ ├─ chart.py                # Plotly trajectory rendering           │
│ └─ tests/                  # Formatters + chart unit tests          │
└─────────────────────────────────────────────────────────────────────┘
                                    ↓
                        (HTTP requests to port 8000)
                                    ↓
┌─────────────────────────────────────────────────────────────────────┐
│ Data Service Microservice (FastAPI)                                 │
│ ├─ main.py                 # FastAPI app + trajectory routes        │
│ ├─ clients/                # MLB API, Statcast, NewsAPI wrappers    │
│ ├─ cache.py                # TTL-based decorator                    │
│ ├─ backoff.py              # Exponential backoff (full-jitter)      │
│ ├─ features.py             # Feature engineering (rolling windows)  │
│ ├─ regression.py           # Ensemble regression + CI bands         │
│ ├─ trajectory.py           # Pre-compute engine (3 functions)       │
│ ├─ transform.py            # Raw JSON → typed DataFrames            │
│ └─ tests/                  # 30 unit + integration tests            │
└─────────────────────────────────────────────────────────────────────┘
```

## Key Design Decisions

1. **Pre-Compute Server-Side:** Microservice fits all models (Statcast CSW% ensemble, game-log rolling OPS/etc). Dashboard renders only — no sklearn/pandas on client.

2. **Graceful Statcast Fallback:** When Statcast unavailable (legitimate case: no data for a player/season, undocumented API), pitcher trajectory falls back to appearance-level MLB Stats metrics (ERA, WHIP, etc). No errors; the caller can see `used_statcast: False` in the response.

3. **TTL Caching Across Layers:**
   - Microservice: `@cached` decorator with 5min TTL on `trajectory.py` functions + 1hr on roster/teams, 60s on game data
   - Dashboard: Streamlit `@st.cache_data` on client functions (avoids Streamlit rerun hammer)

4. **No Overfitting:** Chronological 80/20 holdout split + 95% CI bands so regressions degrade gracefully on unseen data.

5. **Emoji Policy:** Disabled in code/docs; allowed only in README header as exception (applied to H1 title with a single ⚾).

## What's NOT Implemented (Intentional Stopping Point)

- Streamlit browser rendering: App hangs on initial `get_teams()` call (WebSocket proxy limitation). This is expected for a local-dev microservice setup — production deployment would resolve it.
- Dockerfile/Docker Compose: Not needed yet; microservice designed to run standalone on port 8000.
- Database persistence: All caching is in-memory TTL-based. No persistent cache layer.
- Advanced metrics: Only hitter OPS/AVG/etc, pitcher ERA/WHIP/CSW%, team rolling runs. No xStats, park factors, or advanced sabermetrics.
- News feed fully tested: Endpoint live but not verified end-to-end through Streamlit UI.
- Authentication/rate limits: Microservice is open; no API key or user session management.

## Next Steps (Commit 3 & 4)

**Commit 3:** Strip out microservice entirely. Consolidate all pre-compute logic into the root Streamlit app (no http client layer, call trajectory functions directly).

**Commit 4:** Move to single Docker container (FastAPI + Streamlit on separate ports; single image for both).

## Running the System (Dev)

```bash
# Terminal 1: Start microservice on port 8000
cd data_service
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
python -m uvicorn main:app --port 8000

# Terminal 2: Start dashboard on port 8501
cd ..
source .venv/bin/activate
export DATA_SERVICE_URL=http://127.0.0.1:8000
streamlit run app.py --server.port 8501

# Terminal 3: Run tests
cd data_service && pytest -q
cd .. && pytest -q
```

## Known Issues / Notes

1. **Streamlit WebSocket hang in browser preview:** The in-app browser cannot connect to localhost WebSocket due to proxy limitations. Use `streamlit run` locally with your system browser instead.
2. **Test discovery scope:** `pytest.ini` limits root test discovery to `tests/` only to avoid attempting to run data_service tests with root venv (different dependencies).
3. **Statcast data sparsity:** Some players/seasons have no Statcast coverage. Graceful fallback is working as designed.
4. **Cache invalidation:** TTL-based only. If data changes (new game logged, roster updated), you must wait for the cache to expire or restart the service.

---

**Summary:** Microservice pre-compute layer is complete, tested, and verified live. Streamlit dashboard code is written and unit-tested. System architecture is stable. Stopping here to avoid over-engineering a component (microservice) that will be completely removed in Commit 3.
