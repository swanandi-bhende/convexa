"use client";

import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis, Legend } from "recharts";
import { ReferenceLine } from "recharts";

interface RoundPoint {
  round: number;
  bull: number;
  bear: number;
}

interface RoundHistoryProps {
  rounds?: RoundPoint[];
}

const fallbackRounds: RoundPoint[] = [
  { round: 1, bull: 54, bear: 46 },
  { round: 2, bull: 58, bear: 49 },
  { round: 3, bull: 61, bear: 55 },
  { round: 4, bull: 63, bear: 59 },
];

export function RoundHistory({ rounds }: RoundHistoryProps) {
  const data = rounds && rounds.length > 0 ? rounds : fallbackRounds;

  return (
    <section className="rounded-3xl border border-slate-200/70 bg-white p-6 shadow-[0_8px_24px_rgba(33,42,60,0.09)]">
      <p className="text-xs font-semibold uppercase tracking-[0.25em] text-slate-500">Round History</p>
      <div className="mt-4 h-64 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 8, right: 8, left: 4, bottom: 8 }}>
            <XAxis dataKey="round" tickLine={false} axisLine={false} stroke="#738195" />
            <YAxis tickLine={false} axisLine={false} stroke="#738195" />
            <Tooltip />
            <Legend />
            <ReferenceLine y={70} stroke="#f0b35f" strokeDasharray="6 6" />
            <Line type="monotone" dataKey="bull" stroke="#3f70ff" strokeWidth={3} dot={false} name="Bull conviction" />
            <Line type="monotone" dataKey="bear" stroke="#f3653a" strokeWidth={3} dot={false} name="Bear conviction" />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}
