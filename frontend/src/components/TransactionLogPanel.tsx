"use client";

import React from "react";
import { formatHash, formatShortTime } from "@/lib/format";
import { useDebateStore } from "@/store/debateStore";

function toneForType(type: string) {
  if (type === "deposit") {
    return "text-emerald-200 bg-emerald-500/10 border-emerald-400/20";
  }

  if (type === "confirmation") {
    return "text-amber-200 bg-amber-500/10 border-amber-400/20";
  }

  return "text-white/70 bg-white/8 border-white/10";
}

export function TransactionLogPanel() {
  const { state } = useDebateStore();
  const transactions = state.transactions.slice(0, 8);

  return (
    <section className="glass-card-strong rounded-[28px] p-5 sm:p-6">
      <p className="text-xs uppercase tracking-[0.4em] text-white/40">Transaction log</p>
      <h3 className="mt-2 font-display text-4xl text-white">On-chain activity</h3>

      <div className="mt-5 space-y-3">
        {transactions.length ? (
          transactions.map((entry) => (
            <article key={entry.hash} className="rounded-[20px] border border-white/8 bg-white/5 p-4">
              <div className="flex items-center justify-between gap-3">
                <span className={`rounded-full border px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.35em] ${toneForType(entry.type)}`}>
                  {entry.type}
                </span>
                <span className="text-xs text-white/45">{formatShortTime(entry.timestamp)}</span>
              </div>
              <p className="mt-3 text-sm text-white/80">{entry.label}</p>
              <p className="mt-2 font-mono text-xs text-white/45">{formatHash(entry.hash)}</p>
            </article>
          ))
        ) : (
          <div className="rounded-[20px] border border-dashed border-white/10 bg-white/4 p-6 text-sm text-white/45">
            No transactions yet. Deposits and conviction confirmations will stream in here live.
          </div>
        )}
      </div>
    </section>
  );
}
