> A full-stack MLB analytics platform that ingests public sports data into a PostgreSQL cache, powers interactive player and leaderboard analysis, and evaluates time-series forecasting models with rolling features and leakage-aware validation.

[![Python](https://img.shields.io/badge/Python-3.12%2B-3776AB?logo=python&logoColor=white)](#)
[![Streamlit](https://img.shields.io/badge/Streamlit-dashboard-FF4B4B?logo=streamlit&logoColor=white)](#)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Neon-4169E1?logo=postgresql&logoColor=white)](#)
[![GitHub Actions](https://img.shields.io/badge/GitHub_Actions-ETL_automation-2088FF?logo=githubactions&logoColor=white)](#)
[![Tests](https://img.shields.io/badge/tests-pytest-success)](#)


## This Project

Public sports-data APIs are useful for exploration but are a poor direct backend for an interactive analytics product: they can be slow and incomplete for historical records and/or rate-limited during dashboard requests. This project separates data acquisition from user-facing analysis while using a macro-service architecture design.

My data-engineering layer uses cache-aware ingestion and scheduled workflow pipelines to load public messy, semi-structured MLB, Statcast, and RSS data into a Neon PostgreSQL analytics data mart. It applies idempotent upserts, retry/backoff controls, and dataset-specific freshness policies so that historical data can be retrieved reliably without repeatedly calling upstream sources.

My analytics layer uses this curated datastore to compute and explain KPIs, rate- and count-stat aggregations, season leaderboards, historical time series, rolling sabermetrics, team/player cohorts, and interactive visualizations. Counting statistics are aggregated by summation, while rate statistics are aggregated by mean so multi-player comparisons remain statistically interpretable. You can check it out on the streamlit link. Note that the streamlit is a prototype dashboard with all frontend being ported to Vercel, so elements of the macro-service communicating with the datastore may break.

The machine-learning layer treats player performance as an ordered time-series regression problem. It transforms player game logs and Statcast observations into rolling targets and feature matrices containing wOBA-style offensive aggregates, FIP-oriented pitching measures, momentum, rest days, home/away context, velocity, whiff rate, and batted-ball-quality variables. Candidate regressors—including Ridge, SVR, Huber, Gaussian Process Regression, Random Forest, HistGradientBoosting, and ensemble baselines—are evaluated with chronological train/validation splits and walk-forward cross-validation. Performance is reported with \(R^2\), RMSE, and MAE to compare predictive fit and absolute forecast error without temporal leakage.

---

## Analytical and ML computations

If you want to know more about the mathematics I used in the data selection, and especially in the machine learning side, see below.

### Metric-aware cohort aggregation

For a selected player cohort, cumulative counting statistics are summed across players:

$$
C_{\text{cohort}} = \sum_{p=1}^{P} C_p
$$

where $\(C_p\)$ is a counting statistic for player \(p\), such as home runs, RBIs, strikeouts, innings pitched, or earned runs. Rate statistics are aggregated as a mean across the selected players:

$$
R_{\text{cohort}} = \frac{1}{P}\sum_{p=1}^{P} R_p
$$

where $\(R_p\)$ may be batting average, on-base percentage, OPS, ERA, WHIP, xBA, hard-hit percentage, CSW percentage, or whiff percentage. This avoids treating rate statistics as additive quantities.

### Rolling performance targets

The forecasting workflow converts ordered game or appearance observations into rolling performance targets. For a target metric $\(y_t\)$ and a trailing window of $\(w\)$ observations:

$$
\bar{y}_{t}^{(w)} = \frac{1}{w}\sum_{i=t-w+1}^{t} y_i
$$

This smoothing reduces game-to-game variance and creates a time-dependent target that can represent recent hitter or pitcher performance.

### Momentum features

Recent momentum is computed as another short rolling transformation of the target:

$$
m_t^{(k)} = 
\frac{1}{k}\sum_{i=t-k+1}^{t}\bar{y}_{i}^{(w)}
$$

where $\(k\)$ is a short momentum window and $\(\bar{y}_{i}^{(w)}\)$ is the rolling performance target. This gives the model a feature representing recent direction and persistence in performance.

### Weighted on-base average-style offense

The analytics workflow computes a rolling weighted offensive aggregate from plate-appearance outcomes:

$$
\text{wOBA}^{*} = \frac{0.690\text{BB} + 0.722\text{HBP} + 0.888\text{(1B)} + 1.271\text{(2B)} + 1.616\text{(3B)} + 2.101\text{HR}}{\text{AB} + \text{BB} + \text{SF} + \text{HBP}}
$$

where \(BB\) is walks, \(HBP\) is hit by pitch, \(1B\), \(2B\), and \(3B\) are singles, doubles, and triples, \(HR\) is home runs, \(AB\) is at-bats, and \(SF\) is sacrifice flies.

The asterisk indicates that this is a wOBA-style weighted aggregate using fixed weights in the modeling workflow, rather than a claim that the calculation uses annually recalibrated official league wOBA weights.

### Fielding Independent Pitching-oriented target

For pitchers, the workflow computes a rolling FIP-oriented target:

$$
\text{FIP} = \frac{13\text{HR} + 3(\text{BB} + \text{HBP}) - 2\text{K}}{\text{IP}} + C
$$

where \(HR\) is home runs allowed, \(BB\) is walks, \(HBP\) is hit batters, \(K\) is strikeouts, \(IP\) is innings pitched, and \(C\) is a league adjustment constant.

This target emphasizes outcomes that are more directly connected to pitching events than ERA alone.

### Supervised learning feature matrix

For each time step \(t\), the model receives an ordered feature vector:

$$
X_t =
[
a_t,\,
m_t,\,
h_t,\,
r_t,\,
s_t
]
$$

where:

* $$a_t$$ = appearance number or time index
* $$m_t$$ = recent momentum feature
* $$h_t$$ = home/away context
* $$r_t$$ = rest days since the previous appearance
* $$s_t$$ = vector of available Statcast-derived tracking features, split into:
  * $$\text{EV}$$ = exit velocity
  * $$\text{xBA}$$ = expected batting average
  * $$\text{HH}\%$$ = hard-hit rate percentage
  * $$\text{Whiff}\%$$ = whiff rate percentage
  * $$\text{Chase}\%$$ = chase rate percentage
  * $$v_{\text{pitch}}$$ = velocity of the pitch

The supervised regression task learns a mapping:

$$
\hat{y}_{t+1} = f(X_t)
$$

where $(\hat{y}_{t+1})$ is the predicted future rolling performance value.


### Ridge regression baseline

Standard ridge regression provides a regularized linear baseline:

$$
\underset{\beta}{\text{minimize}} \, \left[ \sum_{i=1}^{n} (y_i - X_i\beta)^2 + \lambda \|\beta\|_2^2 \right]
$$



The first term minimizes squared prediction error, while the $\(L_2\)$ penalty shrinks large coefficients and helps stabilize estimates when features are correlated.

### Ensemble regression baseline

The earlier ensemble baseline combines predictions from Support Vector Regression, Huber Regression, and Gaussian Process Regression:

$$
\hat{y}_{\text{ensemble}}=0.35\hat{y}_{\text{SVR}}+0.35\hat{y}_{\text{Huber}}+0.30\hat{y}_{\text{GPR}}
$$

The model-evaluation workflow compares this fixed weighted blend against candidate regressors rather than assuming it is optimal.

### Gaussian Process predictive uncertainty

When Gaussian Process Regression is used, the model provides both a mean prediction and an estimated predictive standard deviation:

$$
\hat{y}_t \sim \mathcal{N}(\mu_t, \sigma_t^2)
$$

A visual uncertainty interval can be expressed as:

$$
\mu_t \pm 1.96\sigma_t
$$

This produces an approximate 95% model-based predictive interval under the model assumptions.

### Chronological train/validation split

Time-series data is partitioned chronologically rather than randomly:

$$
\mathcal{D}_{\text{train}}=\{(X_t, y_t)\}_{t=1}^{T_{\text{train}}}
$$

$$
\mathcal{D}_{\text{validation}}=\{(X_t, y_t)\}_{t=T_{\text{train}}+1}^{T}
$$

This ensures that future performance observations are not used to predict earlier observations.

### Walk-forward cross-validation

Walk-forward validation repeatedly expands the training window and evaluates on later observations:

$$
\text{Fold}_j:
\quad
\{1, \ldots, t_j\}
\rightarrow
\{t_j + 1, \ldots, t_j + h\}
$$

Each fold trains only on data available before the validation period. This prevents look-ahead leakage and better reflects the real forecasting task.

### Mean Absolute Error

MAE measures the average absolute prediction error:

$$
\text{MAE}=\frac{1}{n}\sum_{i=1}^{n}\left|y_i - \hat{y}_i\right|
$$

It remains in the native units of the target and is easy to interpret.

### Root Mean Squared Error

RMSE penalizes larger forecast errors more strongly:

$$
\text{RMSE}=\sqrt{\frac{1}{n}\sum_{i=1}^{n}(y_i - \hat{y}_i)^2}
$$

It is useful when large misses are more costly than small misses.

### Coefficient of determination

The coefficient of determination compares model error with the variability in the validation target:

$$
R^2 = 1 -\frac{\sum_{i=1}^{n}(y_i-\hat{y}_i)^2}{\sum_{i=1}^{n}(y_i-\bar{y})^2}
$$

where $\(\bar{y}\)$ is the validation-set mean.

For smoothed rolling targets, validation values can have low variance. In those cases, \(R^2\) can be volatile or negative even if MAE and RMSE indicate relatively small absolute forecast errors. Therefore, the workflow reports \(R^2\), RMSE, and MAE together.


---

It ingests and normalizes roster history, season statistics, Statcast telemetry aggregates, leaderboard inputs, and team news into Neon PostgreSQL. To mitigate expensive upstream calls, the frontend reads a cache-aware data layer rather than repeatedly making expensive upstream calls. 

- Compare one or more player selections within a team and historical timeline.
- Aggregate counting statistics by sum and rate statistics by mean across a selected cohort.
- Visualize multi-metric season trends for hitting, pitching, and supported Statcast metrics.
- Produce player-cohort forecasts from a configurable training window and forecast horizon.
- Display team- and season-scoped Insights leaderboards across 22 hitting, pitching, and Statcast metrics.
- Ingest MLB.com and SB Nation team news every six hours, then serve the dashboard from PostgreSQL rather than fetching news during user interaction.
- Support local operation, Streamlit deployment, standalone FastAPI access, GitHub Actions ingestion, and a Next.js/Vercel interface.
Only include the Next.js/Vercel sentence if the UI is intentionally part of the product. If it is a prototype or a migration in progress, write this instead:

text

- Include an in-progress Next.js/Vercel client experiment alongside the primary Streamlit analytics application.
