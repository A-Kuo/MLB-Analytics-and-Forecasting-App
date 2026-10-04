const ids = [108,109,110,111,112,113,114,115,116,117,118,119,120,121,133,134,135,136,137,138,139,140,141,142,143,144,145,146,147,158].join(",");
const targets = {
  "insights leaderboard (30 teams, HR, 2025)": `http://localhost:3000/api/insights?metric=homeRuns&group=hitting&season=2025&teamIds=${ids}&limit=10`,
  "insights leaderboard (30 teams, ERA, 2025)": `http://localhost:3000/api/insights?metric=era&group=pitching&season=2025&teamIds=${ids}&limit=10`,
  "team news (10 teams)": `http://localhost:3000/api/news?teamIds=${ids.split(",").slice(0,10).join(",")}&days=7&limit=10`,
  "live MLB Stats API (1 team roster call, baseline)": `https://statsapi.mlb.com/api/v1/teams/147/roster?rosterType=fullRoster&season=2025`,
};
const pct = (a, p) => a[Math.min(a.length - 1, Math.ceil(p * a.length) - 1)];
for (const [name, url] of Object.entries(targets)) {
  const r0 = await fetch(url); if (!r0.ok) { console.log(name, "-> HTTP", r0.status); continue; } await r0.text(); // warm-up (route compile / connection)
  const t = [];
  for (let i = 0; i < 20; i++) { const s = performance.now(); const r = await fetch(url); await r.text(); t.push(performance.now() - s); }
  t.sort((a, b) => a - b);
  console.log(`${name}: median ${pct(t, .5).toFixed(0)} ms | p95 ${pct(t, .95).toFixed(0)} ms | max ${t.at(-1).toFixed(0)} ms (n=20)`);
}
