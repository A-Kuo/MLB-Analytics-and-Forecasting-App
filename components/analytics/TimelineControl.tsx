"use client";

import { useEffect, useState } from "react";

type TimelineControlProps = {
  minYear: number;
  maxYear: number;
  startYear: number;
  endYear: number;
  onChange: (start: number, end: number) => void;
};

/** Year-range control -- the Node/React analogue of utils/timeline.
 * year_range_control. Simplified to two number inputs rather than a
 * draggable dual-handle slider (no native HTML equivalent).
 *
 * Each input keeps its own local text state so every keystroke is echoed
 * back to the field immediately. Binding the input directly to the
 * validated `startYear`/`endYear` props (only updating them when a
 * keystroke's value is in range) blocks typing: a partially-typed number
 * that's transiently out of range (e.g. typing "1" then "19" while minYear
 * is 1901) never fires onChange, so React redraws the input back to its old
 * value and only the native step arrows -- which always land on an
 * in-range number -- keep working. Here, a valid value still commits
 * immediately (so arrow stepping and in-range typing feel the same as
 * before); an out-of-range or unparsable value just isn't committed yet,
 * and blur reverts the field to the last committed value rather than
 * applying it, matching the original "invalid or inverted edit reverts"
 * behavior. */
export function TimelineControl({ minYear, maxYear, startYear, endYear, onChange }: TimelineControlProps) {
  const [startText, setStartText] = useState(String(startYear));
  const [endText, setEndText] = useState(String(endYear));

  useEffect(() => setStartText(String(startYear)), [startYear]);
  useEffect(() => setEndText(String(endYear)), [endYear]);

  function handleStartChange(value: string) {
    setStartText(value);
    const next = parseInt(value, 10);
    if (!isNaN(next) && minYear <= next && next <= endYear) onChange(next, endYear);
  }

  function handleEndChange(value: string) {
    setEndText(value);
    const next = parseInt(value, 10);
    if (!isNaN(next) && startYear <= next && next <= maxYear) onChange(startYear, next);
  }

  return (
    <div className="flex items-center gap-md">
      <label className="flex items-center gap-xs text-body-sm text-steel">
        Start year
        <input
          type="number"
          min={minYear}
          max={maxYear}
          value={startText}
          onChange={(e) => handleStartChange(e.target.value)}
          onBlur={() => setStartText(String(startYear))}
          onKeyDown={(e) => {
            if (e.key === "Enter") e.currentTarget.blur();
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
          value={endText}
          onChange={(e) => handleEndChange(e.target.value)}
          onBlur={() => setEndText(String(endYear))}
          onKeyDown={(e) => {
            if (e.key === "Enter") e.currentTarget.blur();
          }}
          className="w-24 rounded-md border border-hairline-strong bg-surface px-2 py-1 text-body-sm text-ink"
        />
      </label>
    </div>
  );
}
