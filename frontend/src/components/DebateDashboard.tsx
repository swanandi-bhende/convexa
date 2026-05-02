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
      ? "bg-surface-container-low text-emerald-700"
      : state.connectionStatus === "reconnecting"
        ? "bg-surface-container-low text-amber-700"
        : state.connectionStatus === "disconnected"
          ? "bg-surface-container-low text-rose-700"
          : "bg-surface-container-low text-on-surface-variant";

  return <span className={`rounded-full px-4 py-2 text-xs font-semibold uppercase tracking-[0.35em] ${tone}`}>{state.connectionStatus}</span>;
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
        <header className="glass-card relative z-10 flex flex-wrap items-center justify-between gap-4 rounded-[20px] px-5 py-4 sm:px-6">
          <div>
            <p className="font-display text-2xl text-on-surface">Mercator</p>
            <p className="text-[10px] uppercase tracking-[0.45em] text-on-surface-variant">Debate registry</p>
          </div>

          <div className="flex flex-wrap items-center gap-3 text-xs uppercase tracking-[0.25em] text-on-surface-variant">
            <span className="rounded-full bg-surface-container-low px-3 py-2 text-on-surface">Session {sessionId}</span>
            <span className="rounded-full bg-surface-container-low px-3 py-2 text-on-surface">{networkName}</span>
            <ConnectionBadge />
          </div>
        </header>

        <section className="relative overflow-hidden rounded-[34px] bg-surface p-6 sm:p-8">
          <div className="grid items-center gap-8 lg:grid-cols-[1.1fr_0.9fr]">
            <div>
              <p className="text-xs uppercase tracking-[0.35em] text-primary">Live editorial brief</p>
              <h1 className="mt-3 font-display text-5xl leading-[1.05] text-on-surface sm:text-6xl">
                The art of
                <span className="block text-secondary italic">intentional conviction.</span>
              </h1>
              <p className="mt-4 max-w-2xl text-base leading-7 text-on-surface-variant sm:text-lg">
                Real-time rounds, onchain settlement, and transparent capital allocation for both sides of the market narrative.
              </p>
              <div className="mt-6 flex flex-wrap gap-3">
                <span className="rounded-full bg-surface-container-low px-4 py-2 text-xs uppercase tracking-[0.25em] text-on-surface">Round {state.currentRound || debateState?.currentRound || 0}</span>
                <span className="rounded-full bg-surface-container-low px-4 py-2 text-xs uppercase tracking-[0.25em] text-on-surface">Bull {state.currentBullScore}</span>
                <span className="rounded-full bg-surface-container-low px-4 py-2 text-xs uppercase tracking-[0.25em] text-on-surface">Bear {state.currentBearScore}</span>
              </div>
            </div>

            <div className="relative">
              <div className="rounded-[24px] editorial-gradient p-6 text-on-primary shadow-[0_10px_40px_rgba(34,25,26,0.14)]">
                <p className="text-xs uppercase tracking-[0.3em] text-on-primary/80">Session snapshot</p>
                <p className="mt-3 font-display text-4xl">{sessionId}</p>
                <p className="mt-2 text-sm text-on-primary/85">{networkName}</p>
              </div>
              <div className="absolute -bottom-5 -left-6 -z-10 h-28 w-52 rotate-[-6deg] rounded-[20px] bg-surface-container-high" />
            </div>
          </div>
        </section>

        <div className="grid gap-6">
          <section id="debate" className="grid gap-6 xl:grid-cols-2">
            <DebatePanel side="bull" />
            <DebatePanel side="bear" />
          </section>

          <section id="meter">
            <ConvictionMeter />
          </section>

          <section id="insights" className="grid gap-6">
            <div className="grid gap-6 xl:grid-cols-2">
              <StakePanel />
              <TransactionLog />
            </div>
            <RoundHistory />
          </section>
        </div>

        <section className="glass-card rounded-[28px] p-5 sm:p-6">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-xs uppercase tracking-[0.35em] text-on-surface-variant">Live snapshot</p>
              <h2 className="mt-2 font-display text-3xl text-on-surface">Debate headline</h2>
            </div>
            <div className="rounded-full bg-surface-container-low px-3 py-2 text-xs text-on-surface">
              Round {state.currentRound || debateState?.currentRound || 0} | Bull {state.currentBullScore} | Bear {state.currentBearScore}
            </div>
          </div>
        </section>

        <section className="rounded-[28px] editorial-gradient px-6 py-10 text-center text-on-primary sm:px-10">
          <h2 className="font-display text-4xl sm:text-5xl">Ready to curate your strategy?</h2>
          <p className="mx-auto mt-3 max-w-2xl text-sm text-on-primary/85 sm:text-base">
            Stake, observe conviction movement, and track settlement outcomes from a single editorial command center.
          </p>
        </section>
      </div>
    </main>
  );
}
