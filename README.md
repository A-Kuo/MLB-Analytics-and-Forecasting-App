# ⚾ Baseball Analytics Dashboard

> A live-updating, player-centric baseball analytics dashboard built with Panel (HoloViz), a probabilistic scikit-learn regression ensemble, and a real-time sports news feed. Designed as the first module of a broader sports analytics pipeline (MLB → NFL → NBA).

---

## Project Overview

This is a webapp, mobile app, and web dashboard that ingests live and historical MLB data from the **MLB Stats API** (no key required) and pitch-by-pitch/batted-ball data from **Baseball Savant (Statcast)** to model a player's performance trajectory across a season. A blended ensemble (SVR + Huber + Gaussian Process regressors) fits a trend line with a 95% confidence band, validated on a chronological holdout rather than fit blindly to all available data.

---

## Scope

**Team → season → individual player** is the primary flow: KPI cards, a regression-overlaid trend chart, and a per-game log for one selected player. A secondary **Team Trends** tab shows 10-game rolling runs scored/allowed for the selected team as a whole. Individual pitchers get pitching (defense) metrics and individual hitters get batting (offense) metrics automatically, based on roster position.

---

## Mandatory Criteria

- **Live data fetching**: Player game logs refresh in near-real-time via the MLB Stats API upon game post
- **Team logo rendering**: Team selector includes official MLB team logos fetched from the MLB CDN
- **Regression overlay with uncertainty**: Dotted ensemble trend line + shaded 95% CI band, validated on a chronological 80/20 holdout, on every trajectory chart
- **Filterable news feed**: Toggleable live headlines filtered by selected team name keywords
- **Individual player drill-down**: Team + season selection narrows to a roster; selecting a player renders their own KPIs, trend chart, and game log
- **Team-level rolling aggregates**: 10-game rolling runs scored (offense) and runs allowed (defense) for the selected team

---

## Panel Live Dashboard

Check it out here:



---

## Kaggle Test Environment

Check out all the math testing that went behind this app

https://www.kaggle.com/code/augustinekuo/mlb-analytics-predictive-eda-and-regression/

---

## Architecture

```
baseball-analytics-dashboard/
│
├── app.py                  # Panel entry point — wires components together reactively
├── requirements.txt
├── requirements-dev.txt    # + pytest
├── README.md
│
├── config/
│   └── teams.json          # Team metadata: IDs, names, colors, logo URLs, news keywords
│
├── api/
│   ├── mlb_client.py       # MLB Stats API wrapper (roster, game log, season stats, team schedule/linescore)
│   ├── statcast_client.py  # Baseball Savant pitch-level CSV wrapper (pitcher CSW%, batter EV/xBA/hard-hit)
│   ├── news_client.py      # NewsAPI (if keyed) or public RSS fallback
│   └── cache_manager.py    # TTL-based response caching decorator
│
├── models/
│   └── regression.py       # SVR + Huber + GaussianProcess ensemble, chronological holdout, 95% CI
│
├── components/              # Panel components (param-reactive, not Streamlit widgets)
│   ├── sidebar.py           # Team/season/player selectors with logo, as a param.Parameterized
│   ├── metrics_panel.py     # KPI cards (AVG/OBP/SLG/OPS or ERA/WHIP/K9 depending on player)
│   ├── line_chart.py        # Plotly trajectory chart: CI band, train/holdout markers, cutoff line
│   ├── team_trends.py       # Team-level rolling offense/defense trajectory charts
│   ├── game_log.py          # Per-game box score table for the selected player
│   └── news_feed.py         # Toggleable live news feed component
│
├── utils/
│   ├── features.py          # Feature engineering: rolling windows, momentum, CSW/whiff, team rolling runs
│   ├── filters.py           # Hitter/pitcher metric-set logic
│   └── formatters.py        # Stat formatting helpers (.287, 3.45, etc.)
│
└── tests/
    ├── test_regression.py
    ├── test_features.py
    └── test_formatters.py
```

---

## Data Sources

| Source | Use | Auth |
|---|---|---|
| [MLB Stats API](https://statsapi.mlb.com/api/) | Rosters, player game logs, season stats, team schedule/linescore | None (public) |
| [Baseball Savant](https://baseballsavant.mlb.com/statcast_search) (Statcast CSV export) | Pitch-level CSW%, exit velocity, xBA, hard-hit%, spin rate | None, but **undocumented/unofficial** — see note below |
| MLB CDN (`mlbstatic.com/team-logos`) | Team logos | None (public) |
| [NewsAPI](https://newsapi.org/) or MLB.com news RSS | Sports headlines | Free-tier API key optional — RSS fallback needs none |

**Live game polling**: game logs are cached with a 60-second TTL; Statcast pulls are cached for 1 hour (`api/cache_manager.py`), so newly posted games surface on the next reactive refresh without hammering either API.

> **Statcast reliability note**: Baseball Savant has no documented, stable public API — `statcast_client.py` hits its CSV search endpoint directly. This is confirmed working as of this writing, but it can change or rate-limit without notice. Every caller treats a failed/empty Statcast response as a legitimate "unavailable" case and falls back to MLB Stats API metrics rather than erroring — see [Regression & Trajectory Engines](#regression--trajectory-engines).

---

## Dashboard Layout

### Sidebar (left panel)
- **Team selector** — dropdown with team logo thumbnail + full name
- **Season selector** — year picker (default: current season)
- **Player selector** — roster for the selected team/season; drives the Player tab
- **News feed toggle** — on/off switch

### Player tab
- **KPI cards**: AVG · OBP · SLG · OPS · HR · RBI · K · BB (hitters) or ERA · WHIP · K/9 · BB/9 · W · L (pitchers), from MLB Stats API season stats
- **Performance Trend chart**:
  - Hitters — rolling (10-appearance) AVG/OBP/SLG/OPS/etc., regressed on `[appearance_num, momentum_3, is_home, rest_days, rolling_ev, rolling_xba, rolling_hard_hit]`
  - Pitchers — rolling (25-pitch) CSW% from pitch-by-pitch Statcast, regressed on `[pitch_index, momentum_csw_5, rolling_whiff, rolling_velo, rolling_spin]`; falls back to the appearance-level ERA/WHIP/etc. metric dropdown (Ridge-era style, now on the same ensemble) if Statcast is unavailable for that pitcher/season
  - Every chart: solid markers = training points, diamond markers = holdout points, dotted line = blended ensemble trend, shaded band = 95% CI, vertical dashed line = train/holdout cutoff, title shows holdout R²/RMSE
- **Game Log** (expandable): per-game box score — Hitters: Date · Opponent · AB · H · HR · RBI · BB · K · AVG. Pitchers: Date · Opponent · IP · H · ER · K · BB · ERA

### Team Trends tab
- 10-game rolling **runs scored** (offense) and **runs allowed** (defense) for the selected team, from `/schedule?hydrate=linescore,team`, same ensemble + CI + holdout treatment

### News Feed (toggleable)
- Pulls latest headlines (NewsAPI if `NEWS_API_KEY` is set, otherwise MLB.com's public news RSS)
- Filters to headlines containing the selected team's name/city
- Cached for 5 minutes

---

## Metrics Reference

### Batting (Offense)
| Metric | Description |
|---|---|
| AVG | Batting average (H / AB) |
| OBP | On-base percentage |
| SLG | Slugging percentage |
| OPS | OBP + SLG |
| HR | Home runs |
| RBI | Runs batted in |
| K | Strikeouts |
| BB | Walks |

### Pitching (Defense)
| Metric | Description |
|---|---|
| CSW% | Called-Strike + Whiff rate — primary *trajectory* metric (pitch-level, 25-pitch rolling), avoids the small-sample volatility of raw game-level ERA |
| ERA | Earned run average — season KPI card, and the trend-chart fallback when Statcast is unavailable |
| WHIP | Walks + hits per inning pitched |
| K/9 | Strikeouts per 9 innings |
| BB/9 | Walks per 9 innings |
| W / L | Wins / losses |

> FIP is not returned by the MLB Stats API's season-stats endpoint and is deferred to a future upgrade.

---

## Regression & Trajectory Engines

```python
# models/regression.py — the blended ensemble (simplified)
svr    = SVR(kernel="rbf").fit(X_train, y_train)          # weight 0.35
huber  = HuberRegressor().fit(X_train, y_train)            # weight 0.35
gpr    = GaussianProcessRegressor(RBF() + WhiteKernel())   # weight 0.30, also gives predictive std
gpr.fit(X_train, y_train)

blended = 0.35 * svr.predict(X) + 0.35 * huber.predict(X) + 0.30 * gpr.predict(X)
ci_band = 1.96 * gpr_predictive_std   # ~95% confidence band
```

- **Offensive trajectory engine (hitters)**: target is rolling AVG/OPS/etc. (10-appearance window); features blend MLB Stats API game-log context (`appearance_num`, `momentum_3`, `is_home`, `rest_days`) with Statcast batted-ball quality (`rolling_ev`, `rolling_xba`, `rolling_hard_hit`). If Statcast is unavailable those three columns are neutral zeros, and the model still fits on the MLB Stats API features alone.
- **Defensive trajectory engine (pitchers)**: target is CSW% (25-pitch rolling window) at pitch-level granularity from Baseball Savant, bounded to `[0, 1]`; features are `pitch_index`, `momentum_csw_5`, `rolling_whiff`, `rolling_velo`, `rolling_spin`. Falls back to the appearance-level ERA/WHIP/K/BB/IP/ER dropdown (same ensemble, single-feature) when Statcast can't be fetched.
- **Team aggregates (offense & defense)**: target is 10-game rolling `team_total_runs` / `opp_total_runs` from the schedule+linescore endpoint, single-feature (`game_num`) ensemble.
- **Validation**: every fit uses a chronological 80/20 train/holdout split (never a random shuffle — this is time-series data). The chart marks the cutoff with a vertical line, styles holdout points as diamonds vs. training circles, and reports holdout R²/RMSE in the chart title, not just an in-sample fit.
- Ridge regression (`fit_regression`) is retained in `models/regression.py` for the simple single-feature case and is still unit tested.

> **Note on R² on rolling targets**: rolling-window metrics (AVG, CSW%, etc.) are inherently smooth/autocorrelated, so a small holdout window can have very low variance — R² can look dramatically negative even when the absolute error (RMSE) is small, because R² is normalized by holdout variance, not by the metric's natural scale. That's expected statistical behavior on this kind of target, not a bug.

---

## V1 Roadmap

| Phase | Feature | Status |
|---|---|---|
| v1.0 | Team/season/player selectors with live roster + logo | Done |
| v1.0 | Individual player KPI cards, game log | Done |
| v1.0 | Toggleable news feed with team keyword filtering | Done |
| v1.1 | Offensive trajectory engine (hitters): rolling AVG/OPS + Statcast batted-ball features | Done |
| v1.1 | Defensive trajectory engine (pitchers): pitch-level CSW% via Statcast, with ERA/WHIP fallback | Done |
| v1.1 | Team-level rolling offense/defense aggregates | Done |
| v1.1 | SVR + Huber + GaussianProcess ensemble with 95% CI and chronological holdout validation | Done |

---

## Setup

```bash
git clone https://github.com/A-Kuo/baseball-analytics-dashboard
cd baseball-analytics-dashboard
python -m venv .venv && source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt

# Optional: add a NewsAPI key — without it, the news feed uses MLB.com's public RSS feed
cp .env.example .env  # then edit .env to add NEWS_API_KEY

panel serve app.py --show --autoreload
```

Run the test suite:

```bash
pip install -r requirements-dev.txt
pytest
```

### Core Dependencies

```
panel>=1.4
pandas>=2.0
scikit-learn>=1.4
plotly>=5.20
requests>=2.31
python-dotenv>=1.0
feedparser>=6.0
```

No additional dependencies were needed for the ensemble/Statcast upgrade — `SVR`, `HuberRegressor`, and `GaussianProcessRegressor` all ship with `scikit-learn`, and Statcast is fetched as CSV over `requests`/`pandas`.

---

## Related Projects


---

## Notes

- The MLB Stats API is fully public and does not require authentication for read access
- Baseball Savant's CSV search endpoint is unofficial/undocumented; treat it as best-effort and always behind a graceful fallback (see the Statcast reliability note above)
- Live game data typically posts within 5–10 minutes of completion
- Team logos are served directly from MLB's CDN; no static assets needed
- The news feed keyword filter uses simple substring matching on headline text; a future upgrade could use NER or fuzzy matching for team aliases (e.g., "Sox" → "Boston Red Sox")
