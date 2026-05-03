import Link from "next/link";

export default function AboutPage() {
  return (
    <div className="space-y-8">
      <section className="rounded-[2rem] border border-slate-200/70 bg-white p-8 shadow-[0_16px_32px_rgba(33,42,60,0.08)]">
        <p className="text-xs font-semibold uppercase tracking-[0.28em] text-slate-500">Presentation</p>
        <h1 className="mt-3 text-4xl font-semibold tracking-tight text-slate-950">About Convexa</h1>
        <p className="mt-4 max-w-3xl leading-7 text-slate-600">
          Convexa turns autonomous market reasoning into transparent, score-based debates between Bull and Bear agents.
          It combines live argument generation, judge scoring, conviction tracking, and optional stake settlement.
        </p>
      </section>

      <section className="grid gap-6 lg:grid-cols-3">
        <article className="rounded-2xl border border-slate-200/70 bg-white p-6 shadow-[0_8px_24px_rgba(33,42,60,0.06)]">
          <h2 className="text-xl font-semibold text-slate-900">Problem</h2>
          <p className="mt-3 text-sm leading-6 text-slate-600">Market narratives are noisy, subjective, and hard to validate in real time.</p>
        </article>
        <article className="rounded-2xl border border-slate-200/70 bg-white p-6 shadow-[0_8px_24px_rgba(33,42,60,0.06)]">
          <h2 className="text-xl font-semibold text-slate-900">Solution</h2>
          <p className="mt-3 text-sm leading-6 text-slate-600">Autonomous agent debate rounds with judge verdicts and transparent conviction metrics.</p>
        </article>
        <article className="rounded-2xl border border-slate-200/70 bg-white p-6 shadow-[0_8px_24px_rgba(33,42,60,0.06)]">
          <h2 className="text-xl font-semibold text-slate-900">Tech Stack</h2>
          <p className="mt-3 text-sm leading-6 text-slate-600">Next.js, TypeScript, SQLite APIs, Unichain contracts, and live event updates.</p>
        </article>
      </section>

      <section className="rounded-[2rem] bg-slate-950 p-6 text-white shadow-[0_14px_28px_rgba(15,23,42,0.22)]">
        <h2 className="text-xl font-semibold">Contracts and Links</h2>
        <div className="mt-4 flex flex-wrap gap-3 text-sm">
          <Link href="https://unichain-sepolia.blockscout.com/address/0x1709ce3a1c4506F6889C797dde6Cb9e0950173ED" className="rounded-full bg-white/10 px-4 py-2 transition hover:bg-white/15">
            ConvictionTracker
          </Link>
          <Link href="https://unichain-sepolia.blockscout.com/address/0xBB7bD22Aa37E05979c3858540048e99bCa98CEF9" className="rounded-full bg-white/10 px-4 py-2 transition hover:bg-white/15">
            DebateEscrow
          </Link>
        </div>
      </section>
    </div>
  );
}
