"use client";

import Image from "next/image";
import { useEffect, useMemo, useState } from "react";

import { ForecastChart } from "@/components/analytics/ForecastChart";
import { KpiCards } from "@/components/analytics/KpiCards";
import { PlayerSelector } from "@/components/analytics/PlayerSelector";
import { TimelineControl } from "@/components/analytics/TimelineControl";
import { TrendChart } from "@/components/analytics/TrendChart";
import {
  getAggregateForecast,
  getAggregateKpi,
  getAggregateSeries,
  getTeamRoster,
  getTeams,
  type ForecastPayload,
  type RosterEntry,
  type Team,
} from "@/lib/api";
import { HITTING_METRICS, PITCHING_METRICS, type MetricGroup } from "@/lib/metrics";
import { resolvePlayersInRange } from "@/lib/roster";
import { useNewsTeamIds } from "@/lib/newsContext";

const EARLIEST_SEASON = 1901;
const FORECAST_HORIZON_YEARS = 10;

function groupForSelection(selectedIds: Set<number>, roster: RosterEntry[]): MetricGroup {
  const rosterById = new Map(roster.map((p) => [p.id, p]));
  let pitchers = 0;
  let hitters = 0;
  for (const id of selectedIds) {
    if (rosterById.get(id)?.is_pitcher) pitchers++;
    else hitters++;
  }
  return pitchers > hitters ? "pitching" : "hitting";
}

export default function AnalyticsPage() {
  const currentSeason = new Date().getFullYear();
  const [teams, setTeams] = useState<Team[] | null>(null);
  const [teamId, setTeamId] = useState<number | null>(null);
  const [roster, setRoster] = useState<RosterEntry[]>([]);
  const [startYear, setStartYear] = useState(EARLIEST_SEASON);
  const [endYear, setEndYear] = useState(currentSeason);
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [error, setError] = useState<string | null>(null);

  const [kpiValues, setKpiValues] = useState<Record<string, number | null> | null>(null);
  const [kpiLoading, setKpiLoading] = useState(false);

  const [trendMetrics, setTrendMetrics] = useState<Set<string>>(new Set());
  const [trendData, setTrendData] = useState<Record<string, { years: number[]; values: number[] }> | null>(null);
  const [trendLoading, setTrendLoading] = useState(false);

  const [forecastEnd, setForecastEnd] = useState(currentSeason + FORECAST_HORIZON_YEARS);
  const [forecastMetrics, setForecastMetrics] = useState<Set<string>>(new Set());
  const [forecastData, setForecastData] = useState<Record<string, ForecastPayload> | null>(null);
  const [forecastLoading, setForecastLoading] = useState(false);

  const { setTeamIds } = useNewsTeamIds();

  useEffect(() => {
    getTeams()
      .then(setTeams)
      .catch((err: Error) => setError(err.message));
  }, []);

  useEffect(() => {
    if (teamId === null) return;
    setSelectedIds(new Set());
    getTeamRoster(teamId)
      .then(setRoster)
      .catch((err: Error) => setError(err.message));
    setTeamIds([teamId]);
  }, [teamId, setTeamIds]);

  const selectedGroup = useMemo(() => groupForSelection(selectedIds, roster), [selectedIds, roster]);
  const metrics = selectedGroup === "pitching" ? PITCHING_METRICS : HITTING_METRICS;
  const playerIds = useMemo(() => [...selectedIds], [selectedIds]);

  async function handleCalculateKpi() {
    if (playerIds.length === 0) return;
    setKpiLoading(true);
    try {
      const entries = await Promise.all(
        metrics.map(async ([key]) => [key, await getAggregateKpi(playerIds, key, selectedGroup, startYear, endYear)] as const),
      );
      setKpiValues(Object.fromEntries(entries));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to calculate KPIs");
    } finally {
      setKpiLoading(false);
    }
  }

  async function handleVisualizeTrend() {
    if (playerIds.length === 0 || trendMetrics.size === 0) return;
    setTrendLoading(true);
    try {
      const entries = await Promise.all(
        [...trendMetrics].map(
          async (key) => [key, await getAggregateSeries(playerIds, key, selectedGroup, startYear, endYear)] as const,
        ),
      );
      setTrendData(Object.fromEntries(entries));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch trend data");
    } finally {
      setTrendLoading(false);
    }
  }

  async function handleForecast() {
    if (playerIds.length === 0 || forecastMetrics.size === 0 || forecastEnd <= endYear) return;
    setForecastLoading(true);
    try {
      const entries = await Promise.all(
        [...forecastMetrics].map(
          async (key) =>
            [key, await getAggregateForecast(playerIds, key, selectedGroup, startYear, endYear, forecastEnd)] as const,
        ),
      );
      setForecastData(Object.fromEntries(entries));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to compute forecast");
    } finally {
      setForecastLoading(false);
    }
  }

  const acronymByMetric = Object.fromEntries(metrics);

  return (
    <div className="mx-auto flex max-w-[1280px] flex-col gap-xl px-6 py-xl">
      <div>
        <h1 className="text-heading-1 text-ink-deep">Analytics and Forecasts</h1>
        <p className="text-subtitle text-slate">
          Team/player comparison, Aggregate KPI, Performance Trend, and Forecast.
        </p>
      </div>

      {error && <p className="text-body-sm text-semantic-error">{error}</p>}

      <section>
        <h2 className="mb-md text-heading-5 text-ink-deep">Team</h2>
        {teams === null ? (
          <p className="text-body-sm text-steel">Loading teams…</p>
        ) : (
          <div className="flex items-center gap-sm">
            <select
              value={teamId ?? ""}
              onChange={(e) => setTeamId(e.target.value ? parseInt(e.target.value, 10) : null)}
              className="rounded-md border border-hairline-strong bg-surface px-3 py-1.5 text-body-sm text-ink"
            >
              <option value="">Choose a team</option>
              {[...teams].sort((a, b) => a.name.localeCompare(b.name)).map((t) => (
                <option key={t.id} value={t.id}>
                  {t.name}
                </option>
              ))}
            </select>
            {teamId !== null && (
              <Image
                src={teams.find((t) => t.id === teamId)?.logo_url ?? ""}
                alt=""
                width={40}
                height={40}
                unoptimized
              />
            )}
          </div>
        )}
      </section>

      {teamId !== null && (
        <>
          <section>
            <h2 className="mb-md text-heading-5 text-ink-deep">Timeline</h2>
            <TimelineControl
              minYear={EARLIEST_SEASON}
              maxYear={currentSeason}
              startYear={startYear}
              endYear={endYear}
              onChange={(s, e) => {
                setStartYear(s);
                setEndYear(e);
                setSelectedIds(new Set());
              }}
            />
          </section>

          <section>
            <h2 className="mb-md text-heading-5 text-ink-deep">Player</h2>
            <PlayerSelector
              roster={roster}
              startYear={startYear}
              endYear={endYear}
              selectedIds={selectedIds}
              onChange={setSelectedIds}
            />
            <p className="mt-xs text-micro text-stone">
              {selectedIds.size} player{selectedIds.size === 1 ? "" : "s"} selected
              {selectedIds.size > 0 ? ` -- showing ${selectedGroup} metrics` : ""}
            </p>
          </section>

          <section>
            <h2 className="mb-md text-heading-5 text-ink-deep">Aggregate KPI</h2>
            <button
              type="button"
              onClick={handleCalculateKpi}
              disabled={selectedIds.size === 0 || kpiLoading}
              className="mb-md rounded-md bg-mlb-red px-4 py-2 text-body-sm-medium text-white hover:bg-mlb-red-hover disabled:opacity-50"
            >
              {kpiLoading ? "Calculating…" : "Calculate"}
            </button>
            {selectedIds.size === 0 ? (
              <p className="text-body-sm text-stone">Select one or more players, then press Calculate.</p>
            ) : (
              <KpiCards metrics={metrics} values={kpiValues} />
            )}
          </section>

          <section>
            <h2 className="mb-md text-heading-5 text-ink-deep">Performance Trend</h2>
            <div className="mb-md flex flex-wrap gap-sm">
              {metrics.map(([key, acronym]) => (
                <label key={key} className="flex cursor-pointer items-center gap-1 text-body-sm text-ink">
                  <input
                    type="checkbox"
                    checked={trendMetrics.has(key)}
                    onChange={(e) => {
                      const next = new Set(trendMetrics);
                      if (e.target.checked) next.add(key);
                      else next.delete(key);
                      setTrendMetrics(next);
                    }}
                    className="accent-mlb-red"
                  />
                  {acronym}
                </label>
              ))}
            </div>
            <button
              type="button"
              onClick={handleVisualizeTrend}
              disabled={selectedIds.size === 0 || trendMetrics.size === 0 || trendLoading}
              className="mb-md rounded-md bg-mlb-red px-4 py-2 text-body-sm-medium text-white hover:bg-mlb-red-hover disabled:opacity-50"
            >
              {trendLoading ? "Loading…" : "Visualize"}
            </button>
            {trendData && Object.keys(trendData).length > 0 && (
              <TrendChart
                seriesByMetric={trendData}
                acronymByMetric={acronymByMetric}
                title={`${teams?.find((t) => t.id === teamId)?.name ?? ""} — ${startYear} to ${endYear}`}
              />
            )}
          </section>

          <section>
            <h2 className="mb-md text-heading-5 text-ink-deep">Forecast</h2>
            <div className="mb-md flex items-center gap-sm">
              <label className="flex items-center gap-xs text-body-sm text-steel">
                Forecast horizon (year)
                <input
                  type="number"
                  min={endYear + 1}
                  max={currentSeason + FORECAST_HORIZON_YEARS}
                  value={forecastEnd}
                  onChange={(e) => setForecastEnd(parseInt(e.target.value, 10))}
                  className="w-24 rounded-md border border-hairline-strong bg-surface px-2 py-1 text-body-sm text-ink"
                />
              </label>
            </div>
            <div className="mb-md flex flex-wrap gap-sm">
              {metrics.map(([key, acronym]) => (
                <label key={key} className="flex cursor-pointer items-center gap-1 text-body-sm text-ink">
                  <input
                    type="checkbox"
                    checked={forecastMetrics.has(key)}
                    onChange={(e) => {
                      const next = new Set(forecastMetrics);
                      if (e.target.checked) next.add(key);
                      else next.delete(key);
                      setForecastMetrics(next);
                    }}
                    className="accent-mlb-red"
                  />
                  {acronym}
                </label>
              ))}
            </div>
            <button
              type="button"
              onClick={handleForecast}
              disabled={selectedIds.size === 0 || forecastMetrics.size === 0 || forecastEnd <= endYear || forecastLoading}
              className="mb-md rounded-md bg-mlb-red px-4 py-2 text-body-sm-medium text-white hover:bg-mlb-red-hover disabled:opacity-50"
            >
              {forecastLoading ? "Fitting forecast…" : "Forecast"}
            </button>
            {forecastData && Object.keys(forecastData).length > 0 && (
              <ForecastChart
                forecastByMetric={forecastData}
                acronymByMetric={acronymByMetric}
                title={`${teams?.find((t) => t.id === teamId)?.name ?? ""} — forecast ${endYear} to ${forecastEnd}`}
              />
            )}
          </section>
        </>
      )}
    </div>
  );
}
