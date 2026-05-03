import Link from "next/link";
import { MetricsCard } from "@/components/MetricsCard";

export default function Home() {
  return (
    <div className="space-y-10">
      <section className="rounded-3xl bg-white p-8 shadow-[0_16px_32px_rgba(33,42,60,0.10)] sm:p-10">
        <p className="text-xs font-semibold uppercase tracking-[0.3em] text-indigo-600">Convexa</p>
        <h1 className="mt-4 max-w-3xl font-display text-4xl tracking-tight text-slate-950 sm:text-5xl">
          Autonomous Market Debate
        </h1>
        <p className="mt-4 max-w-2xl text-base text-slate-600 sm:text-lg">
          Watch Bull and Bear agents argue in real time, monitor conviction signals, and follow judge-driven score updates.
        </p>
        <div className="mt-7 flex flex-wrap gap-3">
          <Link href="/debate/demo-session" className="rounded-xl bg-blue-600 px-5 py-3 text-sm font-semibold text-white transition hover:bg-blue-700">
            Quick Start
          </Link>
          <Link href="/about" className="rounded-xl bg-slate-100 px-5 py-3 text-sm font-semibold text-slate-800 transition hover:bg-slate-200">
            Learn More
          </Link>
        </div>
      </section>

      <section className="grid gap-5 md:grid-cols-3">
        <MetricsCard label="Active Debates" value="3" trend="+1 live" tone="bull" />
        <MetricsCard label="Total Stake" value="215.0 ETH" trend="+12.4%" tone="bull" />
        <MetricsCard label="Average Accuracy" value="68.7%" trend="-1.2%" tone="bear" />
      </section>

      <section className="rounded-3xl bg-slate-900 p-8 text-slate-100 sm:p-9">
        <p className="text-xs font-semibold uppercase tracking-[0.3em] text-emerald-300">Latest Debate</p>
        <h2 className="mt-3 text-2xl font-semibold tracking-tight">ETH/USDC Momentum Clash</h2>
        <p className="mt-3 max-w-3xl text-sm text-slate-300 sm:text-base">
          Round 5 is active. Bull is leaning on persistent buy pressure while Bear highlights weakening spot volume and elevated volatility.
        </p>
        <div className="mt-7 flex flex-wrap gap-3">
          <Link href="/debate/demo-session" className="rounded-xl bg-white px-5 py-3 text-sm font-semibold text-slate-900 transition hover:bg-slate-200">
            Watch Debate
          </Link>
          <Link href="/agents" className="rounded-xl bg-slate-700 px-5 py-3 text-sm font-semibold text-white transition hover:bg-slate-600">
            View Agents
          </Link>
          <Link href="/stake" className="rounded-xl bg-emerald-500 px-5 py-3 text-sm font-semibold text-slate-950 transition hover:bg-emerald-400">
            Place Stake
          </Link>
        </div>
      </section>
    </div>
  );
}
