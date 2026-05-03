interface AgentRow {
  name: string;
  side: "Bull" | "Bear";
  accuracy: number;
  wins: number;
  avgConfidence: number;
}

interface AgentLeaderboardProps {
  rows: AgentRow[];
}

export function AgentLeaderboard({ rows }: AgentLeaderboardProps) {
  return (
    <section className="rounded-3xl bg-white p-6 shadow-[0_8px_24px_rgba(33,42,60,0.08)]">
      <h2 className="text-xl font-semibold tracking-tight text-slate-900">Agent Leaderboard</h2>
      <div className="mt-5 overflow-x-auto">
        <table className="w-full min-w-[560px] text-left text-sm">
          <thead className="text-slate-500">
            <tr>
              <th className="py-2">Agent</th>
              <th className="py-2">Side</th>
              <th className="py-2">Accuracy</th>
              <th className="py-2">Wins</th>
              <th className="py-2">Avg Confidence</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.name} className="border-t border-slate-100">
                <td className="py-3 font-semibold text-slate-900">{row.name}</td>
                <td className="py-3">
                  <span className={`rounded-full px-2 py-1 text-xs font-semibold ${row.side === "Bull" ? "bg-blue-100 text-blue-700" : "bg-orange-100 text-orange-700"}`}>
                    {row.side}
                  </span>
                </td>
                <td className="py-3 text-slate-700">{row.accuracy}%</td>
                <td className="py-3 text-slate-700">{row.wins}</td>
                <td className="py-3 text-slate-700">{row.avgConfidence}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
