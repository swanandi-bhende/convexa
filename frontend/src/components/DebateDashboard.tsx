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
      ? "border-emerald-400/20 bg-emerald-500/10 text-emerald-100"
      : state.connectionStatus === "reconnecting"
        ? "border-amber-400/20 bg-amber-500/10 text-amber-100"
        : state.connectionStatus === "disconnected"
          ? "border-rose-400/20 bg-rose-500/10 text-rose-100"
          : "border-white/10 bg-white/5 text-white/70";

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
      <div className="mx-auto flex w-full max-w-7xl flex-col gap-6 pb-12 pt-2 lg:gap-8 lg:pb-16 lg:pt-4">
        <header className="glass-card sticky top-4 z-20 flex flex-wrap items-center justify-between gap-4 rounded-full px-5 py-3 sm:px-6">
          <div>
            <p className="font-display text-2xl text-white">Kompass</p>
            <p className="text-[10px] uppercase tracking-[0.45em] text-white/40">Debate registry</p>
          </div>

          <div className="flex flex-wrap items-center gap-2 text-xs uppercase tracking-[0.3em] text-white/55">
            <span className="rounded-full border border-white/10 bg-white/5 px-3 py-2 text-white/75">Session {sessionId}</span>
            <span className="rounded-full border border-white/10 bg-white/5 px-3 py-2 text-white/75">{networkName}</span>
            <ConnectionBadge />
          </div>
        </header>

        <div className="flex flex-col gap-6">
          <section id="debate" className="order-2 grid gap-6 lg:order-1 lg:grid-cols-2">
            <DebatePanel side="bull" />
            <DebatePanel side="bear" />
          </section>

          <section id="meter" className="order-1 lg:order-2">
            <ConvictionMeter />
          </section>

          <section id="insights" className="order-3 grid gap-6 xl:grid-cols-3">
            <StakePanel />
            <RoundHistory />
            <TransactionLog />
          </section>
        </div>

        <section className="glass-card rounded-[28px] p-5 sm:p-6">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-xs uppercase tracking-[0.35em] text-white/35">Live snapshot</p>
              <h2 className="mt-2 font-display text-3xl text-white">Debate headline</h2>
            </div>
            <div className="rounded-full border border-white/10 bg-white/5 px-3 py-2 text-xs text-white/65">
              Round {state.currentRound || debateState?.currentRound || 0} | Bull {state.currentBullScore} | Bear {state.currentBearScore}
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}
