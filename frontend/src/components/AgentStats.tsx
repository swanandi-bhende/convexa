"use client";

import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

interface AgentStatsProps {
  data: Array<{ round: number; bullAccuracy: number; bearAccuracy: number }>;
}

export function AgentStats({ data }: AgentStatsProps) {
  return (
    <section className="rounded-3xl bg-white p-6 shadow-[0_8px_24px_rgba(33,42,60,0.08)]">
      <h2 className="text-xl font-semibold tracking-tight text-slate-900">Accuracy Trend</h2>
      <p className="mt-2 text-sm text-slate-500">Agent accuracy over recent rounds</p>
      <div className="mt-5 h-72">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data}>
            <XAxis dataKey="round" />
            <YAxis domain={[0, 100]} />
            <Tooltip />
            <Line dataKey="bullAccuracy" type="monotone" stroke="#3f70ff" strokeWidth={3} dot={false} />
            <Line dataKey="bearAccuracy" type="monotone" stroke="#f3653a" strokeWidth={3} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}
