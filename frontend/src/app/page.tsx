import Link from "next/link";
import { MetricsCard } from "@/components/MetricsCard";

export default function Home() {
  return (
    <div className="space-y-10">
      <section className="overflow-hidden rounded-[2rem] border border-white/70 bg-linear-to-br from-slate-950 via-slate-900 to-slate-800 p-8 text-white shadow-[0_24px_60px_rgba(15,23,42,0.24)] sm:p-10 lg:p-12">
        <div className="max-w-3xl">
          <p className="text-xs font-semibold uppercase tracking-[0.3em] text-sky-300">Convexa</p>
          <h1 className="mt-4 font-display text-4xl tracking-tight sm:text-5xl lg:text-6xl">
            Autonomous market debate with live conviction scoring.
          </h1>
          <p className="mt-4 max-w-2xl text-base leading-7 text-slate-300 sm:text-lg">
            Watch Bull and Bear agents argue in real time, inspect judge reasoning, and follow settlement signals in a dashboard that feels operational instead of decorative.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link href="/debate/demo-session" className="rounded-full bg-white px-5 py-3 text-sm font-semibold text-slate-950 transition hover:bg-slate-200">
              Open Live Debate
            </Link>
            <Link href="/about" className="rounded-full border border-white/20 bg-white/5 px-5 py-3 text-sm font-semibold text-white transition hover:bg-white/10">
              Learn More
            </Link>
          </div>
        </div>
      </section>

      <section className="grid gap-5 md:grid-cols-3">
        <MetricsCard label="Active Debates" value="3" trend="+1 live" tone="bull" />
        <MetricsCard label="Total Stake" value="215.0 ETH" trend="+12.4%" tone="bull" />
        <MetricsCard label="Average Accuracy" value="68.7%" trend="-1.2%" tone="bear" />
      </section>

      <section className="rounded-[2rem] border border-slate-200/70 bg-white p-8 shadow-[0_16px_32px_rgba(33,42,60,0.08)] sm:p-9">
        <p className="text-xs font-semibold uppercase tracking-[0.3em] text-emerald-300">Latest Debate</p>
        <h2 className="mt-3 text-2xl font-semibold tracking-tight text-slate-950">ETH/USDC Momentum Clash</h2>
        <p className="mt-3 max-w-3xl text-sm leading-7 text-slate-600 sm:text-base">
          Round 5 is active. Bull is leaning on persistent buy pressure while Bear highlights weakening spot volume and elevated volatility. The current session is designed to read like a live control panel, not a generic landing page.
        </p>
        <div className="mt-7 flex flex-wrap gap-3">
          <Link href="/debate/demo-session" className="rounded-full bg-slate-950 px-5 py-3 text-sm font-semibold text-white transition hover:bg-slate-800">
            Watch Debate
          </Link>
          <Link href="/agents" className="rounded-full bg-slate-100 px-5 py-3 text-sm font-semibold text-slate-800 transition hover:bg-slate-200">
            View Agents
          </Link>
          <Link href="/stake" className="rounded-full bg-emerald-500 px-5 py-3 text-sm font-semibold text-slate-950 transition hover:bg-emerald-400">
            Place Stake
          </Link>
        </div>
      </section>
    </div>
  );
}
