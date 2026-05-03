"use client";

import { useMemo, useState } from "react";
import { DebateCard } from "@/components/DebateCard";
import { DebateDetail } from "@/components/DebateDetail";

const debates = [
  { debateId: "db-1001", tokenPair: "ETH/USDC", winner: "Bull" as const, bullScore: 74, bearScore: 62, date: "2026-05-02", duration: "18m" },
  { debateId: "db-1002", tokenPair: "BTC/USDC", winner: "Bear" as const, bullScore: 59, bearScore: 71, date: "2026-05-01", duration: "22m" },
  { debateId: "db-1003", tokenPair: "SOL/USDC", winner: "Bull" as const, bullScore: 76, bearScore: 57, date: "2026-04-30", duration: "16m" },
];

const roundTranscript = [
  { round: 1, bullArgument: "Spot demand expanding with tighter spreads.", bearArgument: "Perp funding suggests over-extension.", verdict: "Slight edge to Bull on liquidity evidence." },
  { round: 2, bullArgument: "ETF-led flows remain net positive.", bearArgument: "Volume quality deteriorated this session.", verdict: "Bear closes gap with volatility argument." },
  { round: 3, bullArgument: "Orderbook resilience held during pullback.", bearArgument: "Macro risk still underpriced.", verdict: "Bull wins by stronger near-term signal alignment." },
];

export default function HistoryPage() {
  const [query, setQuery] = useState("");
  const [selectedDebate, setSelectedDebate] = useState(debates[0]);

  const filtered = useMemo(
    () => debates.filter((debate) => debate.tokenPair.toLowerCase().includes(query.toLowerCase()) || debate.winner.toLowerCase().includes(query.toLowerCase())),
    [query]
  );

  return (
    <div className="space-y-8">
      <section className="rounded-3xl bg-white p-6 shadow-[0_8px_24px_rgba(33,42,60,0.08)]">
        <h1 className="text-3xl font-semibold tracking-tight text-slate-950">Debate History</h1>
        <p className="mt-2 text-slate-600">Search archives by pair, winner, date window, or performance threshold.</p>
        <div className="mt-4 grid gap-3 md:grid-cols-4">
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            className="rounded-xl border border-slate-200 px-3 py-2 text-sm"
            placeholder="Search by token pair or winner"
            aria-label="Search history"
          />
          <input className="rounded-xl border border-slate-200 px-3 py-2 text-sm" placeholder="From date" aria-label="From date" />
          <input className="rounded-xl border border-slate-200 px-3 py-2 text-sm" placeholder="To date" aria-label="To date" />
          <input className="rounded-xl border border-slate-200 px-3 py-2 text-sm" placeholder="Accuracy threshold" aria-label="Accuracy threshold" />
        </div>
      </section>

      <section className="grid gap-6 xl:grid-cols-[1fr_1fr]">
        <div className="space-y-4">
          {filtered.map((debate) => (
            <DebateCard key={debate.debateId} {...debate} onSelect={() => setSelectedDebate(debate)} />
          ))}
        </div>
        <DebateDetail debateId={selectedDebate.debateId} rounds={roundTranscript} />
      </section>
    </div>
  );
}
