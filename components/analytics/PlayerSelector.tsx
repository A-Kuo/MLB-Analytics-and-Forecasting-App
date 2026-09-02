"use client";

import type { RosterEntry } from "@/lib/api";
import { resolvePlayersInRange } from "@/lib/roster";

const POSITION_GROUPS: Record<string, string[]> = {
  Battery: ["P", "C"],
  Infield: ["1B", "2B", "3B", "SS"],
  Outfield: ["LF", "CF", "RF"],
  "Non-Fielders": ["DH", "TWP", "PH", "PR", "UTL"],
};

type PlayerSelectorProps = {
  roster: RosterEntry[];
  startYear: number;
  endYear: number;
  selectedIds: Set<number>;
  onChange: (next: Set<number>) => void;
};

/** Position-group checkboxes + a plain checkbox list of candidates in
 * range -- the Node/React analogue of utils/selection_widgets.
 * render_player_selection, simplified from Streamlit's multiselect +
 * portrait-wall combo to a single scrollable list (a checkbox's own label
 * carries the same "[position] Name (years active)" info the multiselect
 * pills did). Toggling a position checkbox adds/removes that position
 * group's currently-in-range candidates from the selection, same
 * add-or-remove-a-whole-set rule as TeamSelector's bulk checkboxes. */
export function PlayerSelector({ roster, startYear, endYear, selectedIds, onChange }: PlayerSelectorProps) {
  const candidatesByPosition = Object.fromEntries(
    Object.entries(POSITION_GROUPS).flatMap(([, positions]) =>
      positions.map((pos) => [pos, resolvePlayersInRange(roster, startYear, endYear, [pos])]),
    ),
  ) as Record<string, Set<number>>;

  const allCandidates = resolvePlayersInRange(roster, startYear, endYear);
  const rosterById = new Map(roster.map((p) => [p.id, p]));

  function toggleGroup(ids: Set<number>, checked: boolean) {
    const next = new Set(selectedIds);
    if (checked) ids.forEach((id) => next.add(id));
    else ids.forEach((id) => next.delete(id));
    onChange(next);
  }

  const candidateList = [...allCandidates]
    .map((id) => rosterById.get(id))
    .filter((p): p is RosterEntry => Boolean(p))
    .sort((a, b) => a.name.localeCompare(b.name));

  return (
    <div className="flex flex-col gap-md">
      <div className="flex flex-wrap gap-md">
        {Object.entries(POSITION_GROUPS).map(([group, positions]) => (
          <div key={group} className="flex flex-col gap-xs">
            <span className="text-micro-uppercase text-steel">{group}</span>
            <div className="flex flex-wrap gap-sm">
              {positions.map((pos) => {
                const ids = candidatesByPosition[pos] ?? new Set<number>();
                const checked = ids.size > 0 && [...ids].every((id) => selectedIds.has(id));
                return (
                  <label key={pos} className="flex cursor-pointer items-center gap-1 text-body-sm text-ink">
                    <input
                      type="checkbox"
                      checked={checked}
                      disabled={ids.size === 0}
                      onChange={(e) => toggleGroup(ids, e.target.checked)}
                      className="accent-mlb-red"
                    />
                    {pos}
                  </label>
                );
              })}
            </div>
          </div>
        ))}
      </div>

      <div className="max-h-[240px] overflow-y-auto rounded-md border border-hairline p-sm">
        {candidateList.length === 0 ? (
          <p className="text-body-sm text-stone">No players active in this range.</p>
        ) : (
          candidateList.map((p) => {
            const years =
              p.active_year_ranges.length > 0
                ? p.active_year_ranges.map(([s, e]) => `${s}–${e ?? "present"}`).join(", ")
                : "";
            return (
              <label key={p.id} className="flex cursor-pointer items-center gap-2 py-1 text-body-sm text-ink">
                <input
                  type="checkbox"
                  checked={selectedIds.has(p.id)}
                  onChange={(e) => {
                    const next = new Set(selectedIds);
                    if (e.target.checked) next.add(p.id);
                    else next.delete(p.id);
                    onChange(next);
                  }}
                  className="accent-mlb-red"
                />
                [{p.positions.join(", ")}] {p.name} ({years})
              </label>
            );
          })
        )}
      </div>
    </div>
  );
}
