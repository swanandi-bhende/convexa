import { AgentLeaderboard } from "@/components/AgentLeaderboard";
import { AgentStats } from "@/components/AgentStats";

const leaderboardRows = [
  { name: "Bull Core v2", side: "Bull" as const, accuracy: 72.4, wins: 124, avgConfidence: 76.1 },
  { name: "Bear Sentinel v1", side: "Bear" as const, accuracy: 69.8, wins: 109, avgConfidence: 73.5 },
  { name: "Bull Momentum v1", side: "Bull" as const, accuracy: 66.2, wins: 95, avgConfidence: 71.2 },
  { name: "Bear Risk Lens", side: "Bear" as const, accuracy: 64.9, wins: 88, avgConfidence: 69.7 },
];

const trendData = [
  { round: 1, bullAccuracy: 63, bearAccuracy: 58 },
  { round: 2, bullAccuracy: 65, bearAccuracy: 61 },
  { round: 3, bullAccuracy: 68, bearAccuracy: 64 },
  { round: 4, bullAccuracy: 70, bearAccuracy: 66 },
  { round: 5, bullAccuracy: 72, bearAccuracy: 68 },
  { round: 6, bullAccuracy: 74, bearAccuracy: 69 },
];

export default function AgentsPage() {
  return (
    <div className="space-y-8">
      <section className="rounded-[2rem] border border-slate-200/70 bg-white p-7 shadow-[0_8px_24px_rgba(33,42,60,0.08)]">
        <p className="text-xs font-semibold uppercase tracking-[0.28em] text-slate-500">Agent Performance</p>
        <h1 className="mt-3 text-3xl font-semibold tracking-tight text-slate-950">Bull and Bear Leaderboard</h1>
        <div className="mt-5 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <label className="space-y-2 text-sm text-slate-600">
            Pair
            <input className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm outline-none transition focus:border-slate-400" placeholder="Filter token pair" aria-label="Filter token pair" />
          </label>
          <label className="space-y-2 text-sm text-slate-600">
            Start
            <input className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm outline-none transition focus:border-slate-400" placeholder="Start date" aria-label="Start date" />
          </label>
          <label className="space-y-2 text-sm text-slate-600">
            End
            <input className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm outline-none transition focus:border-slate-400" placeholder="End date" aria-label="End date" />
          </label>
          <button className="rounded-xl bg-slate-900 px-4 py-2 text-sm font-semibold text-white transition hover:bg-slate-800">Apply Filters</button>
        </div>
      </section>

      <AgentLeaderboard rows={leaderboardRows} />
      <AgentStats data={trendData} />
    </div>
  );
}
