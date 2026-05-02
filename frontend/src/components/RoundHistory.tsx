"use client";

import React, { useEffect, useMemo, useRef, useState } from "react";
import { useDebateStore } from "@/store/debateStore";

interface RoundHistoryItem {
  roundNumber: number;
  bullScore: number;
  bearScore: number;
  winner: "bull" | "bear" | "tie" | string;
  reasoning: string;
  accuracyBonusApplied: boolean;
  accuracyBonusRecipient: string | null;
  convictionUpdateStatus: string;
  timestamp: number;
  convictionTxHash: string | null;
  microSettlementTxHash: string | null;
  roundDurationSeconds: number | null;
  bullArgument: string | null;
  bearArgument: string | null;
}

interface RoundHistoryResponse {
  sessionId: string | null;
  rounds: RoundHistoryItem[];
}

function formatRelativeTime(timestamp: number) {
  const deltaSeconds = Math.max(0, Math.floor((Date.now() - timestamp) / 1000));

  if (deltaSeconds < 60) {
    return `${deltaSeconds}s ago`;
  }

  const deltaMinutes = Math.floor(deltaSeconds / 60);
  if (deltaMinutes < 60) {
    return `${deltaMinutes}m ago`;
  }

  const deltaHours = Math.floor(deltaMinutes / 60);
  if (deltaHours < 24) {
    return `${deltaHours}h ago`;
  }

  return `${Math.floor(deltaHours / 24)}d ago`;
}

function winnerLabel(winner: RoundHistoryItem["winner"]) {
  if (winner === "bull") {
    return "Bull";
  }

  if (winner === "bear") {
    return "Bear";
  }

  return "Tie";
}

function winnerTone(winner: RoundHistoryItem["winner"]) {
  if (winner === "bull") {
    return "border-emerald-400/20 bg-emerald-400/10 text-emerald-100";
  }

  if (winner === "bear") {
    return "border-rose-400/20 bg-rose-400/10 text-rose-100";
  }

  return "border-white/15 bg-white/5 text-white/80";
}

export function RoundHistory() {
  const { state } = useDebateStore();
  const [history, setHistory] = useState<RoundHistoryResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [showAll, setShowAll] = useState(false);
  const [, setClock] = useState(Date.now());
  const containerRef = useRef<HTMLDivElement | null>(null);
  const latestRoundRef = useRef<number | null>(null);
  const userAtTopRef = useRef(true);

  useEffect(() => {
    const updateClock = window.setInterval(() => setClock(Date.now()), 60000);
    return () => window.clearInterval(updateClock);
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function loadHistory() {
      try {
        const response = await fetch("/api/round-history", { cache: "no-store" });
        if (!response.ok) {
          throw new Error("Unable to load round history");
        }

        const payload = (await response.json()) as RoundHistoryResponse;
        if (!cancelled) {
          setHistory(payload);
          setIsLoading(false);
        }
      } catch {
        if (!cancelled) {
          setHistory(null);
          setIsLoading(false);
        }
      }
    }

    void loadHistory();
    const interval = window.setInterval(loadHistory, 30000);

    return () => {
      cancelled = true;
      window.clearInterval(interval);
    };
  }, []);

  useEffect(() => {
    const currentLatest = history?.rounds[0]?.roundNumber ?? null;
    if (currentLatest !== null && currentLatest !== latestRoundRef.current) {
      latestRoundRef.current = currentLatest;
      if (userAtTopRef.current && containerRef.current) {
        containerRef.current.scrollTo({ top: 0, behavior: "smooth" });
      }
    }
  }, [history]);

  const rounds = history?.rounds ?? state.roundHistory.map((round) => ({
    roundNumber: round.roundNumber,
    bullScore: round.bullScore,
    bearScore: round.bearScore,
    winner: round.winner,
    reasoning: round.judgeReasoning,
    accuracyBonusApplied: false,
    accuracyBonusRecipient: null,
    convictionUpdateStatus: "local",
    timestamp: round.timestamp,
    convictionTxHash: null,
    microSettlementTxHash: null,
    roundDurationSeconds: null,
    bullArgument: null,
    bearArgument: null,
  }));

  const visibleRounds = showAll ? rounds : rounds.slice(0, 6);
  const latestWinner = rounds[0]?.winner ?? "tie";
  const totalRounds = rounds.length;
  const bullWins = rounds.filter((round) => round.winner === "bull").length;
  const bearWins = rounds.filter((round) => round.winner === "bear").length;

  const leadText = useMemo(() => {
    if (!totalRounds) {
      return "Waiting for the first result.";
    }

    if (bullWins === bearWins) {
      return "The board is level.";
    }

    return `${bullWins > bearWins ? "Bull" : "Bear"} leads the archive.`;
  }, [bearWins, bullWins, totalRounds]);

  return (
    <section className="glass-card-strong min-w-0 overflow-hidden rounded-[28px] p-5 sm:p-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.4em] text-slate-500">Round history</p>
          <h3 className="mt-2 font-display text-4xl text-slate-900">Debate chronology</h3>
        </div>
        <div className="flex items-center gap-2 rounded-full border border-slate-200 bg-white px-3 py-2 text-xs text-slate-600">
          <span className={`h-2.5 w-2.5 rounded-full ${latestWinner === "bull" ? "bg-emerald-400" : latestWinner === "bear" ? "bg-rose-400" : "bg-amber-300"}`} />
          {leadText}
        </div>
      </div>

      <div className="mt-5 grid gap-3 sm:grid-cols-3">
        <div className="rounded-[20px] border border-slate-200 bg-white p-4 shadow-[0_10px_30px_rgba(60,48,36,0.05)]">
          <div className="text-xs uppercase tracking-[0.28em] text-slate-500">Total rounds</div>
          <div className="mt-2 font-mono text-3xl text-slate-900">{totalRounds}</div>
        </div>
        <div className="rounded-[20px] border border-emerald-200 bg-emerald-50 p-4">
          <div className="text-xs uppercase tracking-[0.28em] text-emerald-700">Bull wins</div>
          <div className="mt-2 font-mono text-3xl text-emerald-700">{bullWins}</div>
        </div>
        <div className="rounded-[20px] border border-rose-200 bg-rose-50 p-4">
          <div className="text-xs uppercase tracking-[0.28em] text-rose-700">Bear wins</div>
          <div className="mt-2 font-mono text-3xl text-rose-700">{bearWins}</div>
        </div>
      </div>

      <div
        ref={containerRef}
        className="mt-5 max-h-[34rem] space-y-3 overflow-y-auto pr-1"
        onScroll={() => {
          if (!containerRef.current) {
            return;
          }

          userAtTopRef.current = containerRef.current.scrollTop < 24;
        }}
      >
        {isLoading ? (
          <div className="rounded-[24px] border border-slate-200 bg-white p-5 text-sm text-slate-600">Loading round history...</div>
        ) : null}

        {!isLoading && visibleRounds.length === 0 ? (
          <div className="rounded-[24px] border border-slate-200 bg-white p-5 text-sm text-slate-600">No rounds have been recorded yet.</div>
        ) : null}

        {visibleRounds.map((round, index) => {
          const isCurrentRound = round.roundNumber === state.currentRound;
          const bullWidth = `${Math.max(5, round.bullScore)}%`;
          const bearWidth = `${Math.max(5, round.bearScore)}%`;
          const isNewest = index === 0;

          return (
            <article
              key={round.roundNumber}
              className={`rounded-[24px] border p-5 transition ${isCurrentRound ? "border-amber-300/30 bg-amber-50 shadow-[0_0_0_1px_rgba(251,191,36,0.12)]" : "border-slate-200 bg-white"} ${isNewest ? "animate-[slide-down-fade_0.35s_ease-out]" : ""}`}
            >
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="text-xs uppercase tracking-[0.35em] text-slate-500">Round {round.roundNumber}</p>
                  <div className="mt-2 flex flex-wrap items-center gap-2">
                    <span className={`rounded-full border px-3 py-1 text-xs font-medium ${winnerTone(round.winner)}`}>{winnerLabel(round.winner)} wins</span>
                    {round.accuracyBonusApplied ? (
                      <span className="rounded-full border border-cyan-400/20 bg-cyan-400/10 px-3 py-1 text-xs text-cyan-100">
                        Accuracy bonus {round.accuracyBonusRecipient ? `→ ${round.accuracyBonusRecipient}` : "applied"}
                      </span>
                    ) : null}
                    {isCurrentRound ? <span className="rounded-full border border-amber-300/20 bg-amber-300/10 px-3 py-1 text-xs text-amber-100">Current round</span> : null}
                  </div>
                </div>
                <div className="text-right text-xs uppercase tracking-[0.28em] text-white/35">
                  <div>{formatRelativeTime(round.timestamp)}</div>
                  <div className="mt-1 font-mono text-[11px] text-white/50">{round.convictionUpdateStatus}</div>
                </div>
              </div>

              <div className="mt-4 grid gap-4 lg:grid-cols-[1.2fr_0.8fr]">
                <div>
                  <div className="flex items-center justify-between text-sm text-white/70">
                    <span>Bull {round.bullScore}</span>
                    <span>Bear {round.bearScore}</span>
                  </div>
                  <div className="mt-2 h-2 overflow-hidden rounded-full bg-white/6">
                    <div className="flex h-full">
                      <div className="h-full rounded-full bg-linear-to-r from-emerald-500 to-emerald-300" style={{ width: bullWidth }} />
                      <div className="h-full rounded-full bg-linear-to-r from-rose-500 to-rose-300" style={{ width: bearWidth }} />
                    </div>
                  </div>
                  <p className="mt-4 text-sm leading-6 text-slate-600">{round.reasoning}</p>
                </div>

                <div className="space-y-3 rounded-[20px] border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
                  <div className="flex items-center justify-between">
                    <span>Round time</span>
                    <span className="font-mono text-slate-900">{Math.round((round.roundDurationSeconds ?? 0) * 10) / 10 || "--"}s</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>Conviction tx</span>
                    <span className="font-mono text-slate-900">{round.convictionTxHash ? `${round.convictionTxHash.slice(0, 8)}...` : "pending"}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>Micro settlement</span>
                    <span className="font-mono text-slate-900">{round.microSettlementTxHash ? `${round.microSettlementTxHash.slice(0, 8)}...` : "none"}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>Updated</span>
                    <span className="font-mono text-slate-900">{formatRelativeTime(round.timestamp)}</span>
                  </div>
                </div>
              </div>

              <div className="mt-4 grid gap-3 md:grid-cols-2">
                <div className="rounded-[18px] border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-900/90">
                  <div className="text-[11px] uppercase tracking-[0.28em] text-emerald-700">Bull argument</div>
                  <p className="mt-2 leading-6 text-slate-600">{round.bullArgument || "Bull argument is captured in the websocket feed."}</p>
                </div>
                <div className="rounded-[18px] border border-rose-200 bg-rose-50 p-4 text-sm text-rose-900/90">
                  <div className="text-[11px] uppercase tracking-[0.28em] text-rose-700">Bear argument</div>
                  <p className="mt-2 leading-6 text-slate-600">{round.bearArgument || "Bear argument is captured in the websocket feed."}</p>
                </div>
              </div>
            </article>
          );
        })}
      </div>

      {rounds.length > 6 ? (
        <div className="mt-4 flex justify-center">
          <button
            className="rounded-full border border-slate-200 bg-white px-4 py-2 text-sm text-slate-600 transition hover:border-slate-300 hover:text-slate-900"
            onClick={() => setShowAll((value) => !value)}
          >
            {showAll ? "Show fewer" : `Show more (${rounds.length - 6})`}
          </button>
        </div>
      ) : null}
    </section>
  );
}
