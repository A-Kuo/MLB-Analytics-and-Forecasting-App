"use client";

type TimelineControlProps = {
  minYear: number;
  maxYear: number;
  startYear: number;
  endYear: number;
  onChange: (start: number, end: number) => void;
};

/** Year-range control -- the Node/React analogue of utils/timeline.
 * year_range_control. Simplified to two number inputs rather than a
 * draggable dual-handle slider (no native HTML equivalent); an invalid or
 * inverted edit reverts rather than applying, matching the Streamlit
 * behavior exactly. */
export function TimelineControl({ minYear, maxYear, startYear, endYear, onChange }: TimelineControlProps) {
  return (
    <div className="flex items-center gap-md">
      <label className="flex items-center gap-xs text-body-sm text-steel">
        Start year
        <input
          type="number"
          min={minYear}
          max={maxYear}
          value={startYear}
          onChange={(e) => {
            const next = parseInt(e.target.value, 10);
            if (!isNaN(next) && minYear <= next && next <= endYear) onChange(next, endYear);
          }}
          className="w-24 rounded-md border border-hairline-strong bg-surface px-2 py-1 text-body-sm text-ink"
        />
      </label>
      <span className="text-steel">–</span>
      <label className="flex items-center gap-xs text-body-sm text-steel">
        End year
        <input
          type="number"
          min={minYear}
          max={maxYear}
          value={endYear}
          onChange={(e) => {
            const next = parseInt(e.target.value, 10);
            if (!isNaN(next) && startYear <= next && next <= maxYear) onChange(startYear, next);
          }}
          className="w-24 rounded-md border border-hairline-strong bg-surface px-2 py-1 text-body-sm text-ink"
        />
      </label>
    </div>
  );
}
