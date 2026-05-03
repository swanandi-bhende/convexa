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
import { MegaBreadcrumb } from "@/components/MegaBreadcrumb";

export default function DebatePage() {
  const params = useParams<{ debateId: string }>();
  const { state, history, market, loading, error, feedMode, lastUpdateAt } = useDebateData();

  const currentRound = state ? Math.max(1, state.currentRound) : 1;
  const totalRounds = Math.max(currentRound, history.length || currentRound);
  const currentHistory = history.find((item) => item.roundNumber === currentRound) ?? history[0];
  const spread = state ? Math.abs(state.currentBullScore - state.currentBearScore) : 0;
  const leader = !state || state.currentBullScore === state.currentBearScore ? "Tie" : state.currentBullScore > state.currentBearScore ? "Bull" : "Bear";

  const dynamicNarrative = useMemo(() => {
    if (!state) {
      return {
        bull: "Bull agent is waiting for the next actionable signal.",
        bear: "Bear agent is waiting for the next actionable signal.",
      };
    }

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
  }, [currentHistory?.bearArgument, currentHistory?.bullArgument, currentRound, state]);

  if (loading) {
    return (
      <section className="space-y-4" aria-live="polite" aria-busy="true">
        <div className="h-8 w-48 animate-pulse rounded bg-surface-container-high" />
        <div className="grid gap-4 lg:grid-cols-3">
          <div className="h-72 animate-pulse rounded bg-surface-container-high" />
          <div className="h-72 animate-pulse rounded bg-surface-container-high" />
          <div className="h-72 animate-pulse rounded bg-surface-container-high" />
        </div>
      </section>
    );
  }

  if (error || !state || !market) {
    return (
      <section className="bg-primary/10 p-6 text-primary border-l-4 border-primary slide-up-fade">
        <p className="font-semibold">Unable to load debate</p>
        <p className="mt-2 text-sm">{error ?? "Unknown error"}</p>
      </section>
    );
  }

  const feedBadge =
    feedMode === "live"
      ? { label: "Live", tone: "text-bull-500" }
      : feedMode === "replay"
        ? { label: "Replay", tone: "text-primary" }
        : { label: "Polling", tone: "text-tertiary" };

  const secondsAgo = Math.max(0, Math.round((Date.now() - lastUpdateAt) / 1000));
  const updateHint =
    feedMode === "live"
      ? "Websocket is active."
      : feedMode === "replay"
        ? "Feed is in replay mode to keep round progression visible while live stream is unavailable."
        : "Polling fallback is active; waiting for the next backend refresh.";

  return (
    <div className="max-w-7xl mx-auto space-y-12 pb-32 slide-up-fade">
      <MegaBreadcrumb />

      <section className="tonal-card p-8 sm:p-12 relative overflow-hidden group">
        <div className="absolute -left-12 -top-12 w-32 h-32 bg-primary/5 rounded-full transition-transform duration-700 group-hover:scale-150" />
        <div className="relative z-10 flex flex-wrap items-end justify-between gap-6">
          <div>
            <p className="label-md text-on-surface-variant">Live Debate Session</p>
            <h1 className="display-lg text-on-surface mt-2">{params.debateId}</h1>
          </div>
          <div className="flex flex-col items-end gap-2">
            <div className="flex items-center gap-3 label-md">
              <span className="text-on-surface-variant">Round {currentRound}/{totalRounds}</span>
              <span className={feedBadge.tone}>
                {feedBadge.label}
              </span>
            </div>
            <p className="text-sm text-on-surface-variant">{updateHint} Last update {secondsAgo}s ago.</p>
          </div>
        </div>
      </section>

      <section className="grid gap-8 xl:grid-cols-[1fr_380px_1fr]">
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

        <div className="space-y-8 flex flex-col justify-center">
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

      <section className="bg-surface-container-highest p-8">
        <p className="label-md text-secondary mb-4">Orchestrator Analysis</p>
        <p className="body-lg text-on-surface-variant">
          Judge weighting currently favors <strong className="text-on-surface">{leader}</strong>. The conviction spread is <strong className="text-on-surface">{spread}</strong> points. The Orchestrator evaluates settlement finalization once either side reaches the threshold shown in Conviction Tracker.
        </p>
      </section>

      <section className="grid gap-8 lg:grid-cols-[1fr_1.2fr]">
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
