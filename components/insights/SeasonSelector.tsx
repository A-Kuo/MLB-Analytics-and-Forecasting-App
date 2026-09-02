"use client";

// EARLIEST_SEASON matches utils/constants.EARLIEST_SEASON (AL founding --
// MLB Stats API's season-stats coverage goes back this far).
const EARLIEST_SEASON = 1901;

type SeasonSelectorProps = {
  selectedSeason: number;
  onChange: (season: number) => void;
  minYear?: number;
  maxYear?: number;
};

export function SeasonSelector({
  selectedSeason,
  onChange,
  minYear = EARLIEST_SEASON,
  maxYear = new Date().getFullYear(),
}: SeasonSelectorProps) {
  const years = Array.from({ length: maxYear - minYear + 1 }, (_, i) => maxYear - i);

  return (
    <div className="flex items-center gap-3">
      <label htmlFor="season-select" className="text-body-sm-medium text-steel">
        Season:
      </label>
      <select
        id="season-select"
        value={selectedSeason}
        onChange={(e) => onChange(parseInt(e.target.value, 10))}
        className="rounded-md border border-hairline-strong bg-surface px-3 py-1.5 text-body-sm text-ink focus:border-mlb-red focus:outline-none focus:ring-1 focus:ring-mlb-red"
      >
        {years.map((year) => (
          <option key={year} value={year}>
            {year}
          </option>
        ))}
      </select>
    </div>
  );
}

export { EARLIEST_SEASON };
