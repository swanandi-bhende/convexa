"use client";

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
  const { state, history, market, loading, error, wsConnected } = useDebateData();

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
            <span className={`rounded-full px-3 py-1 ${wsConnected ? "bg-emerald-100 text-emerald-700" : "bg-amber-100 text-amber-700"}`}>
              {wsConnected ? "Live" : "Polling"}
            </span>
          </div>
        </div>
      </section>

      <section className="grid gap-6 xl:grid-cols-[1fr_380px_1fr]">
        <BullCard
          name="Bull Agent"
          argument={currentHistory?.bullArgument ?? "Bull agent is preparing the next argument."}
          confidence={Math.min(99, state.currentBullScore)}
          score={state.currentBullScore}
          metrics={["Momentum bias", "Liquidity confidence", `Stake ${state.bullStakeTotalEth.toFixed(2)} ETH`]}
        />

        <div className="space-y-6">
          <MarketSnapshot snapshot={market} />
          <ConvictionTracker bullScore={state.currentBullScore} bearScore={state.currentBearScore} threshold={70} />
        </div>

        <BearCard
          name="Bear Agent"
          argument={currentHistory?.bearArgument ?? "Bear agent is stress-testing the current thesis."}
          confidence={Math.min(99, state.currentBearScore)}
          score={state.currentBearScore}
          metrics={["Drawdown risk", "Volatility warning", `Stake ${state.bearStakeTotalEth.toFixed(2)} ETH`]}
        />
      </section>

      <section className="grid gap-6 lg:grid-cols-[1fr_1.2fr]">
        <JudgeVerdict
          pending={state.currentBullScore === state.currentBearScore}
          round={currentRound}
          bullScore={state.currentBullScore}
          bearScore={state.currentBearScore}
        />
        <RoundHistory rounds={history.map((item) => ({ round: item.roundNumber, bull: item.bullScore, bear: item.bearScore }))} />
      </section>
    </div>
  );
}
