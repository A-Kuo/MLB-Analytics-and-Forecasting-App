"use client";

type MetricTabsProps = {
  selectedGroup: "hitting" | "pitching" | "statcast";
  onChange: (group: "hitting" | "pitching" | "statcast") => void;
  selectedMetric: string;
  onMetricChange: (metric: string) => void;
};

const METRIC_OPTIONS = {
  hitting: [
    { value: "avg", label: "AVG" },
    { value: "obp", label: "OBP" },
    { value: "slg", label: "SLG" },
    { value: "ops", label: "OPS" },
    { value: "homeRuns", label: "HR" },
    { value: "rbi", label: "RBI" },
    { value: "strikeOuts", label: "SO" },
    { value: "baseOnBalls", label: "BB" }
  ],
  pitching: [
    { value: "era", label: "ERA" },
    { value: "whip", label: "WHIP" },
    { value: "strikeOuts", label: "SO" },
    { value: "baseOnBalls", label: "BB" },
    { value: "inningsPitched", label: "IP" },
    { value: "earnedRuns", label: "ER" }
  ],
  statcast: [
    // This is simplified, combining hitting/pitching statcast for the UI, 
    // though the DB layer handles them slightly differently
    { value: "xba", label: "xBA (Hit)" },
    { value: "avgExitVelocity", label: "Exit Vel (Hit)" },
    { value: "hardHitPct", label: "Hard Hit % (Hit)" },
    { value: "barrelPct", label: "Barrel % (Hit)" },
    { value: "cswPct", label: "CSW % (Pitch)" },
    { value: "whiffPct", label: "Whiff % (Pitch)" },
    { value: "chasePct", label: "Chase % (Pitch)" },
    { value: "avgVelocity", label: "Velocity (Pitch)" }
  ]
};

export function MetricTabs({ selectedGroup, onChange, selectedMetric, onMetricChange }: MetricTabsProps) {
  const tabs = [
    { id: "hitting", label: "Hitting" },
    { id: "pitching", label: "Pitching" },
    { id: "statcast", label: "Statcast" }
  ] as const;

  const currentOptions = METRIC_OPTIONS[selectedGroup];

  return (
    <div className="flex flex-col gap-4">
      {/* Group Tabs */}
      <div className="flex rounded-lg bg-gray-900 p-1">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => {
              onChange(tab.id);
              // Auto-select first metric of new group
              onMetricChange(METRIC_OPTIONS[tab.id][0].value);
            }}
            className={`flex-1 rounded-md px-4 py-2 text-sm font-medium transition-colors ${
              selectedGroup === tab.id
                ? "bg-[#e31837] text-white shadow"
                : "text-gray-400 hover:text-white"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Metric Selector */}
      <div className="flex items-center gap-3">
        <label htmlFor="metric-select" className="text-sm font-medium text-gray-400">
          Selected metric:
        </label>
        <select
          id="metric-select"
          value={selectedMetric}
          onChange={(e) => onMetricChange(e.target.value)}
          className="flex-1 rounded-md border border-gray-700 bg-gray-800 px-3 py-2 text-sm text-white focus:border-[#e31837] focus:outline-none focus:ring-1 focus:ring-[#e31837]"
        >
          {currentOptions.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
}
