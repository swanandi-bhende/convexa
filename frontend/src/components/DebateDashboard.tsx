"use client";

import React, { useEffect, useState } from "react";
import { ConvictionMeter } from "@/components/ConvictionMeter";
import { DebatePanel } from "@/components/DebatePanel";
import { RoundHistory } from "@/components/RoundHistory";
import { StakePanel } from "@/components/StakePanel";
import { TransactionLog } from "@/components/TransactionLog";
import { useDebateStore } from "@/store/debateStore";

interface DebateStateResponse {
  sessionId: string | null;
  networkName: string;
  chainId: number;
  currentRound: number;
  currentBullScore: number;
  currentBearScore: number;
  debateActive: boolean;
  bullStakeTotalEth: number;
  bearStakeTotalEth: number;
}

function ConnectionBadge() {
  const { state } = useDebateStore();

  const tone =
    state.connectionStatus === "live"
      ? "border-emerald-200 bg-emerald-50 text-emerald-700"
      : state.connectionStatus === "reconnecting"
        ? "border-amber-200 bg-amber-50 text-amber-700"
        : state.connectionStatus === "disconnected"
          ? "border-rose-200 bg-rose-50 text-rose-700"
          : "border-slate-200 bg-white text-slate-600";

  return <span className={`rounded-full border px-4 py-2 text-xs font-semibold uppercase tracking-[0.35em] ${tone}`}>{state.connectionStatus}</span>;
}

export function DebateDashboard() {
  const { state } = useDebateStore();
  const [debateState, setDebateState] = useState<DebateStateResponse | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadState() {
      try {
        const response = await fetch("/api/debate-state", { cache: "no-store" });
        if (!response.ok) {
          throw new Error("Unable to load debate state");
        }

        const payload = (await response.json()) as DebateStateResponse;
        if (!cancelled) {
          setDebateState(payload);
        }
      } catch {
        if (!cancelled) {
          setDebateState(null);
        }
      }
    }

    void loadState();
    const interval = window.setInterval(loadState, 30000);

    return () => {
      cancelled = true;
      window.clearInterval(interval);
    };
  }, []);

  const sessionId = debateState?.sessionId ?? "loading...";
  const networkName = debateState?.networkName ?? "Unichain Sepolia";

  return (
    <main className="min-h-screen px-4 py-4 text-foreground sm:px-6 lg:px-8">
      <div className="mx-auto flex w-full max-w-7xl flex-col gap-6 pb-12 pt-6 lg:gap-8 lg:pb-16 lg:pt-8">
        <header className="glass-card relative z-10 flex flex-wrap items-center justify-between gap-4 rounded-[20px] px-5 py-3 shadow-[0_10px_35px_rgba(60,48,36,0.08)] sm:px-6">
          <div>
            <p className="font-display text-2xl text-slate-900">Mercator</p>
            <p className="text-[10px] uppercase tracking-[0.45em] text-slate-500">Debate registry</p>
          </div>

          <div className="flex flex-wrap items-center gap-2 text-xs uppercase tracking-[0.3em] text-slate-600">
            <span className="rounded-full border border-slate-200 bg-white/80 px-3 py-2 text-slate-700">Session {sessionId}</span>
            <span className="rounded-full border border-slate-200 bg-white/80 px-3 py-2 text-slate-700">{networkName}</span>
            <ConnectionBadge />
          </div>
        </header>

        <div className="grid gap-6">
          <section id="debate" className="grid gap-6 xl:grid-cols-2">
            <DebatePanel side="bull" />
            <DebatePanel side="bear" />
          </section>

          <section id="meter">
            <ConvictionMeter />
          </section>

          <section id="insights" className="grid gap-6 xl:grid-cols-3">
            <StakePanel />
            <RoundHistory />
            <TransactionLog />
          </section>
        </div>

        <section className="glass-card rounded-[28px] p-5 sm:p-6">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-xs uppercase tracking-[0.35em] text-slate-500">Live snapshot</p>
              <h2 className="mt-2 font-display text-3xl text-slate-900">Debate headline</h2>
            </div>
            <div className="rounded-full border border-slate-200 bg-white/80 px-3 py-2 text-xs text-slate-700">
              Round {state.currentRound || debateState?.currentRound || 0} | Bull {state.currentBullScore} | Bear {state.currentBearScore}
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}
