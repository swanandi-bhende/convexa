"use client";

import { useMemo } from "react";
import { useParams } from "next/navigation";
import { BearCard } from "@/components/BearCard";
import { BullCard } from "@/components/BullCard";
import { JudgeVerdict } from "@/components/JudgeVerdict";
import { MarketSnapshot } from "@/components/MarketSnapshot";
import { ConvictionTracker } from "@/components/ConvictionTracker";
import { RoundHistory } from "@/components/RoundHistory";
import { useDebateData } from "@/hooks/useDebateData";

export default function DebatePage() {
  const params = useParams<{ debateId: string }>();
  const { state, history, market, loading, error, feedMode, lastUpdateAt } = useDebateData();

  if (loading) {
    return (
      <section className="space-y-4" aria-live="polite" aria-busy="true">
        <div className="h-8 w-48 animate-pulse rounded bg-slate-200" />
        <div className="grid gap-4 lg:grid-cols-3">
          <div className="h-72 animate-pulse rounded-3xl bg-slate-200" />
          <div className="h-72 animate-pulse rounded-3xl bg-slate-200" />
          <div className="h-72 animate-pulse rounded-3xl bg-slate-200" />
        </div>
      </section>
    );
  }

  if (error || !state || !market) {
    return (
      <section className="rounded-2xl bg-rose-50 p-6 text-rose-700">
        <p className="font-semibold">Unable to load debate</p>
        <p className="mt-2 text-sm">{error ?? "Unknown error"}</p>
      </section>
    );
  }

  const currentRound = Math.max(1, state.currentRound);
  const totalRounds = Math.max(currentRound, history.length || currentRound);
  const currentHistory = history.find((item) => item.roundNumber === currentRound) ?? history[0];
  const spread = Math.abs(state.currentBullScore - state.currentBearScore);
  const leader = state.currentBullScore === state.currentBearScore ? "Tie" : state.currentBullScore > state.currentBearScore ? "Bull" : "Bear";

  const dynamicNarrative = useMemo(() => {
    const bullLead = state.currentBullScore - state.currentBearScore;
    const bearLead = state.currentBearScore - state.currentBullScore;

    const bullArgument =
      bullLead >= 0
        ? `Round ${currentRound}: Bull claims order-flow confirmation with a ${bullLead}-point lead and argues that follow-through is now a participation signal, not just price noise.`
        : `Round ${currentRound}: Bull is in recovery mode, arguing that risk-reward improved after Bear pressure pushed conviction lower.`;

    const bearArgument =
      bearLead >= 0
        ? `Round ${currentRound}: Bear highlights fragility in momentum and says upside is thin unless new liquidity appears.`
        : `Round ${currentRound}: Bear acknowledges short-term strength but argues the move is extended and prone to mean reversion.`;

    return {
      bull: currentHistory?.bullArgument && currentHistory.bullArgument.trim().length > 20 ? currentHistory.bullArgument : bullArgument,
      bear: currentHistory?.bearArgument && currentHistory.bearArgument.trim().length > 20 ? currentHistory.bearArgument : bearArgument,
    };
  }, [currentHistory?.bearArgument, currentHistory?.bullArgument, currentRound, state.currentBearScore, state.currentBullScore]);

  const feedBadge =
    feedMode === "live"
      ? { label: "Live", tone: "bg-emerald-100 text-emerald-700" }
      : feedMode === "replay"
        ? { label: "Replay", tone: "bg-sky-100 text-sky-700" }
        : { label: "Polling", tone: "bg-amber-100 text-amber-700" };

  const secondsAgo = Math.max(0, Math.round((Date.now() - lastUpdateAt) / 1000));
  const updateHint =
    feedMode === "live"
      ? "Websocket is active."
      : feedMode === "replay"
        ? "Feed is in replay mode to keep round progression visible while live stream is unavailable."
        : "Polling fallback is active; waiting for the next backend refresh.";

  return (
    <div className="space-y-8">
      <section className="rounded-3xl bg-white p-6 shadow-[0_8px_24px_rgba(33,42,60,0.08)] sm:p-8">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.25em] text-slate-500">Live Debate</p>
            <h1 className="mt-2 text-3xl font-semibold tracking-tight text-slate-950">Session {params.debateId}</h1>
          </div>
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.2em]">
            <span className="rounded-full bg-slate-100 px-3 py-1 text-slate-700">Round {currentRound}/{totalRounds}</span>
            <span className={`rounded-full px-3 py-1 ${feedBadge.tone}`}>
              {feedBadge.label}
            </span>
          </div>
        </div>
        <div className="mt-4 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
          <p>{updateHint}</p>
          <p className="mt-1 text-xs uppercase tracking-[0.16em] text-slate-500">Last update {secondsAgo}s ago</p>
        </div>
      </section>

      <section className="grid gap-6 xl:grid-cols-[1fr_380px_1fr]">
        <BullCard
          name="Bull Agent"
          argument={dynamicNarrative.bull}
          confidence={Math.min(99, state.currentBullScore)}
          score={state.currentBullScore}
          metrics={[
            "Momentum bias",
            spread > 0 && leader === "Bull" ? `Leading by ${spread} points` : "Rebuilding conviction",
            `Stake ${state.bullStakeTotalEth.toFixed(2)} ETH`,
          ]}
        />

        <div className="space-y-6">
          <MarketSnapshot snapshot={market} />
          <ConvictionTracker bullScore={state.currentBullScore} bearScore={state.currentBearScore} threshold={70} />
        </div>

        <BearCard
          name="Bear Agent"
          argument={dynamicNarrative.bear}
          confidence={Math.min(99, state.currentBearScore)}
          score={state.currentBearScore}
          metrics={[
            "Drawdown risk",
            spread > 0 && leader === "Bear" ? `Leading by ${spread} points` : "Searching for reversal",
            `Stake ${state.bearStakeTotalEth.toFixed(2)} ETH`,
          ]}
        />
      </section>

      <section className="rounded-3xl border border-slate-200/70 bg-white p-6 shadow-[0_8px_24px_rgba(33,42,60,0.09)]">
        <p className="text-xs font-semibold uppercase tracking-[0.25em] text-slate-500">Why This Round Moved</p>
        <p className="mt-3 text-sm leading-7 text-slate-700">
          Judge weighting currently favors <span className="font-semibold text-slate-900">{leader}</span>. The conviction spread is <span className="font-semibold text-slate-900">{spread}</span> points, and settlement finalization is evaluated once either side reaches the threshold shown in Conviction Tracker.
        </p>
      </section>

      <section className="grid gap-6 lg:grid-cols-[1fr_1.2fr]">
        <JudgeVerdict
          pending={state.currentBullScore === state.currentBearScore}
          round={currentRound}
          bullScore={state.currentBullScore}
          bearScore={state.currentBearScore}
          rationale={currentHistory?.reasoning ?? `Conviction spread is ${spread} and threshold pressure is increasing.`}
        />
        <RoundHistory rounds={history.map((item) => ({ round: item.roundNumber, bull: item.bullScore, bear: item.bearScore }))} />
      </section>
    </div>
  );
}
