"use client";

import Image from "next/image";

import type { Team } from "@/lib/api";

type TeamSelectorProps = {
  teams: Team[];
  selectedTeamIds: Set<number>;
  onChange: (next: Set<number>) => void;
};

const TEAMS_PER_ROW = 6;
const LEAGUES: { key: string; label: string }[] = [
  { key: "AL", label: "American League" },
  { key: "NL", label: "National League" },
];
const DIVISIONS = ["East", "Central", "West"] as const;

/** Toggling a bulk checkbox (All Teams / a league / a division) adds or
 * removes its whole candidate id set from the selection -- ported from
 * utils/selection_widgets.sync_bulk_checkbox. A bulk checkbox's own
 * "checked" state is never stored: it's re-derived every render as
 * "is the current selection already a superset of this group's ids",
 * matching Streamlit's pages/insights.py exactly. */
function toggleGroup(current: Set<number>, groupIds: readonly number[], checked: boolean): Set<number> {
  const next = new Set(current);
  if (checked) {
    for (const id of groupIds) next.add(id);
  } else {
    for (const id of groupIds) next.delete(id);
  }
  return next;
}

function isSuperset(current: Set<number>, groupIds: readonly number[]): boolean {
  return groupIds.length > 0 && groupIds.every((id) => current.has(id));
}

export function TeamSelector({ teams, selectedTeamIds, onChange }: TeamSelectorProps) {
  const orderedTeams = [...teams].sort((a, b) => a.name.localeCompare(b.name));
  const allTeamIds = teams.map((t) => t.id);
  const rows: Team[][] = [];
  for (let i = 0; i < orderedTeams.length; i += TEAMS_PER_ROW) {
    rows.push(orderedTeams.slice(i, i + TEAMS_PER_ROW));
  }

  return (
    <div className="flex flex-col gap-lg">
      {/* 1. Individual team checkboxes, alphabetical, logo + full name */}
      <div className="flex flex-col gap-sm">
        {rows.map((row, i) => (
          <div key={i} className="grid grid-cols-2 gap-sm sm:grid-cols-3 lg:grid-cols-6">
            {row.map((team) => (
              <label
                key={team.id}
                className="flex cursor-pointer items-center gap-xs rounded-md px-xs py-xs text-body-sm text-ink hover:bg-surface-soft"
              >
                <input
                  type="checkbox"
                  checked={selectedTeamIds.has(team.id)}
                  onChange={(e) => {
                    const next = new Set(selectedTeamIds);
                    if (e.target.checked) next.add(team.id);
                    else next.delete(team.id);
                    onChange(next);
                  }}
                  className="accent-mlb-red"
                />
                <Image src={team.logo_url} alt="" width={20} height={20} unoptimized />
                <span className="truncate">{team.name}</span>
              </label>
            ))}
          </div>
        ))}
      </div>

      {/* 2. Bulk-select: All Teams, then League rows paired with division checkboxes */}
      <div className="flex flex-col gap-xs border-t border-hairline pt-md">
        <label className="flex w-fit cursor-pointer items-center gap-xs text-body-sm-medium text-ink">
          <input
            type="checkbox"
            checked={isSuperset(selectedTeamIds, allTeamIds)}
            onChange={(e) => onChange(toggleGroup(selectedTeamIds, allTeamIds, e.target.checked))}
            className="accent-mlb-red"
          />
          All Teams
        </label>

        {LEAGUES.map(({ key: league, label }) => {
          const leagueIds = teams.filter((t) => t.league === league).map((t) => t.id);
          return (
            <div key={league} className="flex flex-wrap items-center gap-md">
              <label className="flex w-48 cursor-pointer items-center gap-xs text-body-sm text-ink">
                <input
                  type="checkbox"
                  checked={isSuperset(selectedTeamIds, leagueIds)}
                  onChange={(e) => onChange(toggleGroup(selectedTeamIds, leagueIds, e.target.checked))}
                  className="accent-mlb-red"
                />
                {label}
              </label>
              {DIVISIONS.map((division) => {
                const divisionIds = teams
                  .filter((t) => t.league === league && t.division === division)
                  .map((t) => t.id);
                return (
                  <label
                    key={division}
                    className="flex cursor-pointer items-center gap-xs text-body-sm text-steel"
                  >
                    <input
                      type="checkbox"
                      checked={isSuperset(selectedTeamIds, divisionIds)}
                      onChange={(e) => onChange(toggleGroup(selectedTeamIds, divisionIds, e.target.checked))}
                      className="accent-mlb-red"
                    />
                    {division}
                  </label>
                );
              })}
            </div>
          );
        })}
      </div>
    </div>
  );
}
