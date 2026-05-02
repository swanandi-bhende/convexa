"use client";

import React from "react";
import { formatTimestamp } from "@/lib/format";
import { useDebateStore } from "@/store/debateStore";

export function RoundHistoryPanel() {
  const { state } = useDebateStore();
  const rounds = state.roundHistory.slice(0, 6);

  return (
    <section className="glass-card-strong rounded-[28px] p-5 sm:p-6">
      <p className="text-xs uppercase tracking-[0.4em] text-white/40">Round history</p>
      <h3 className="mt-2 font-display text-4xl text-white">Recent turns</h3>

      <div className="mt-5 space-y-3">
        {rounds.length ? (
          rounds.map((round) => {
            const winnerTone = round.winner === "bull" ? "text-emerald-200" : round.winner === "bear" ? "text-rose-200" : "text-white/65";

            return (
              <article key={round.roundNumber} className="rounded-[20px] border border-white/8 bg-white/5 p-4">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <p className="text-xs uppercase tracking-[0.35em] text-white/40">Round {round.roundNumber}</p>
                    <p className="mt-1 font-medium text-white/85">{formatTimestamp(round.timestamp)}</p>
                  </div>
                  <span className={`rounded-full border border-white/8 px-3 py-1 text-xs uppercase tracking-[0.3em] ${winnerTone}`}>
                    {round.winner}
                  </span>
                </div>

                <div className="mt-4 grid grid-cols-2 gap-3 text-sm text-white/70">
                  <div className="rounded-[16px] bg-emerald-500/6 p-3">
                    <span className="block text-xs uppercase tracking-[0.3em] text-emerald-200/60">Bull</span>
                    <span className="font-mono text-white">{round.bullScore}</span>
                  </div>
                  <div className="rounded-[16px] bg-rose-500/6 p-3">
                    <span className="block text-xs uppercase tracking-[0.3em] text-rose-200/60">Bear</span>
                    <span className="font-mono text-white">{round.bearScore}</span>
                  </div>
                </div>

                <p className="mt-3 text-sm leading-6 text-white/60">{round.judgeReasoning}</p>
              </article>
            );
          })
        ) : (
          <div className="rounded-[20px] border border-dashed border-white/10 bg-white/4 p-6 text-sm text-white/45">
            No completed rounds yet. The panel will populate as the first conviction update lands on-chain.
          </div>
        )}
      </div>
    </section>
  );
}
