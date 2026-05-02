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

function uniqueRounds(items: RoundHistoryItem[]) {
  const seen = new Set<string>();
  const deduped: RoundHistoryItem[] = [];

  for (const item of items) {
    const key = `${item.roundNumber}:${item.timestamp}`;
    if (seen.has(key)) {
      continue;
    }

    seen.add(key);
    deduped.push(item);
  }

  return deduped;
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
    return "bg-surface text-emerald-700";
  }

  if (winner === "bear") {
    return "bg-surface text-rose-700";
  }

  return "bg-surface text-on-surface-variant";
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

  const rounds = uniqueRounds(history?.rounds ?? state.roundHistory.map((round) => ({
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
  }))).sort((left, right) => right.timestamp - left.timestamp);

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
          <p className="text-xs uppercase tracking-[0.4em] text-on-surface-variant">Round history</p>
          <h3 className="mt-2 font-display text-3xl text-on-surface sm:text-4xl">Debate chronology</h3>
        </div>
        <div className="flex items-center gap-2 rounded-full bg-surface-container-low px-3 py-2 text-xs text-on-surface-variant">
          <span className={`h-2.5 w-2.5 rounded-full ${latestWinner === "bull" ? "bg-emerald-400" : latestWinner === "bear" ? "bg-rose-400" : "bg-amber-300"}`} />
          {leadText}
        </div>
      </div>

      <div className="mt-5 grid gap-3 sm:grid-cols-3">
        <div className="rounded-[20px] bg-surface p-4">
          <div className="text-xs uppercase tracking-[0.28em] text-on-surface-variant">Total rounds</div>
          <div className="mt-2 font-mono text-3xl text-on-surface">{totalRounds}</div>
        </div>
        <div className="rounded-[20px] bg-surface p-4">
          <div className="text-xs uppercase tracking-[0.28em] text-emerald-700">Bull wins</div>
          <div className="mt-2 font-mono text-3xl text-emerald-700">{bullWins}</div>
        </div>
        <div className="rounded-[20px] bg-surface p-4">
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
        {isLoading ? <div className="rounded-[24px] bg-surface p-5 text-sm text-on-surface-variant">Loading round history...</div> : null}

        {!isLoading && visibleRounds.length === 0 ? <div className="rounded-[24px] bg-surface p-5 text-sm text-on-surface-variant">No rounds have been recorded yet.</div> : null}

        {visibleRounds.map((round, index) => {
          const isCurrentRound = round.roundNumber === state.currentRound;
          const bullWidth = `${Math.max(5, round.bullScore)}%`;
          const bearWidth = `${Math.max(5, round.bearScore)}%`;
          const isNewest = index === 0;

          return (
            <article
              key={`${round.roundNumber}-${round.timestamp}-${index}`}
              className={`rounded-[24px] bg-surface p-5 transition ${isCurrentRound ? "bg-surface-container-low" : ""} ${isNewest ? "animate-[slide-down-fade_0.35s_ease-out]" : ""}`}
            >
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="text-xs uppercase tracking-[0.35em] text-on-surface-variant">Round {round.roundNumber}</p>
                  <div className="mt-2 flex flex-wrap items-center gap-2">
                    <span className={`rounded-full px-3 py-1 text-xs font-medium ${winnerTone(round.winner)}`}>{winnerLabel(round.winner)} wins</span>
                    {round.accuracyBonusApplied ? (
                      <span className="rounded-full bg-surface-container-low px-3 py-1 text-xs text-on-surface-variant">
                        Accuracy bonus {round.accuracyBonusRecipient ? `→ ${round.accuracyBonusRecipient}` : "applied"}
                      </span>
                    ) : null}
                    {isCurrentRound ? <span className="rounded-full bg-surface-container-low px-3 py-1 text-xs text-primary">Current round</span> : null}
                  </div>
                </div>
                <div className="text-right text-xs uppercase tracking-[0.28em] text-on-surface-variant">
                  <div>{formatRelativeTime(round.timestamp)}</div>
                  <div className="mt-1 font-mono text-[11px] text-on-surface-variant">{round.convictionUpdateStatus}</div>
                </div>
              </div>

              <div className="mt-4 grid gap-4 lg:grid-cols-[1.2fr_0.8fr]">
                <div>
                  <div className="flex items-center justify-between text-sm text-on-surface-variant">
                    <span>Bull {round.bullScore}</span>
                    <span>Bear {round.bearScore}</span>
                  </div>
                  <div className="mt-2 h-2 overflow-hidden rounded-full bg-surface-container-low">
                    <div className="flex h-full">
                      <div className="h-full rounded-full" style={{ width: bullWidth, background: 'linear-gradient(135deg, rgba(134,79,81,0.95) 0%, rgba(162,103,105,0.95) 100%)' }} />
                      <div className="h-full rounded-full" style={{ width: bearWidth, background: 'linear-gradient(135deg, rgba(141,72,97,0.95) 0%, rgba(109,87,81,0.95) 100%)' }} />
                    </div>
                  </div>
                  <p className="mt-4 text-sm leading-6 text-on-surface-variant">{round.reasoning}</p>
                </div>

                <div className="space-y-3 rounded-[20px] bg-surface-container-low p-4 text-sm text-on-surface-variant">
                  <div className="flex items-center justify-between">
                    <span>Round time</span>
                    <span className="font-mono text-on-surface">{Math.round((round.roundDurationSeconds ?? 0) * 10) / 10 || "--"}s</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>Conviction tx</span>
                    <span className="font-mono text-on-surface">{round.convictionTxHash ? `${round.convictionTxHash.slice(0, 8)}...` : "pending"}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>Micro settlement</span>
                    <span className="font-mono text-on-surface">{round.microSettlementTxHash ? `${round.microSettlementTxHash.slice(0, 8)}...` : "none"}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>Updated</span>
                    <span className="font-mono text-on-surface">{formatRelativeTime(round.timestamp)}</span>
                  </div>
                </div>
              </div>

              <div className="mt-4 grid gap-3 md:grid-cols-2">
                <div className="rounded-[18px] bg-surface-container-low p-4 text-sm text-on-surface-variant">
                  <div className="text-[11px] uppercase tracking-[0.28em] text-secondary">Bull argument</div>
                  <p className="mt-2 leading-6">{round.bullArgument || "Bull argument is captured in the websocket feed."}</p>
                </div>
                <div className="rounded-[18px] bg-surface-container-low p-4 text-sm text-on-surface-variant">
                  <div className="text-[11px] uppercase tracking-[0.28em] text-tertiary">Bear argument</div>
                  <p className="mt-2 leading-6">{round.bearArgument || "Bear argument is captured in the websocket feed."}</p>
                </div>
              </div>
            </article>
          );
        })}
      </div>

      {rounds.length > 6 ? (
        <div className="mt-4 flex justify-center">
          <button
            className="rounded-full bg-surface-container-low px-4 py-2 text-sm text-on-surface transition"
            onClick={() => setShowAll((value) => !value)}
          >
            {showAll ? "Show fewer" : `Show more (${rounds.length - 6})`}
          </button>
        </div>
      ) : null}
    </section>
  );
}
