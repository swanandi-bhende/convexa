"use client";

import React, { useEffect, useMemo, useState } from "react";
import { useDebateStore } from "@/store/debateStore";

const WIN_THRESHOLD = 70;

export function ConvictionMeter() {
  const { state } = useDebateStore();
  const { currentBullScore, currentBearScore, currentRound, connectionStatus } = state;
  const [flashKey, setFlashKey] = useState(0);
  const [prevSignature, setPrevSignature] = useState(`${currentBullScore}:${currentBearScore}`);

  useEffect(() => {
    const nextSignature = `${currentBullScore}:${currentBearScore}`;
    if (nextSignature !== prevSignature) {
      setFlashKey((value) => value + 1);
      setPrevSignature(nextSignature);
    }
  }, [currentBullScore, currentBearScore, prevSignature]);

  const total = Math.max(1, currentBullScore + currentBearScore);
  const bullPercent = (currentBullScore / total) * 100;
  const bearPercent = (currentBearScore / total) * 100;
  const leadingScore = Math.max(currentBullScore, currentBearScore);
  const progressPercent = Math.min(100, (leadingScore / WIN_THRESHOLD) * 100);
  const leader = currentBullScore === currentBearScore ? "tie" : currentBullScore > currentBearScore ? "bull" : "bear";

  const statusPill = useMemo(() => {
    const base = "inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-[0.3em]";
    if (connectionStatus === "live") {
      return (
        <span className={`${base} bg-surface-container-low text-emerald-700`}>
          <span className="live-dot inline-block h-2 w-2 rounded-full bg-emerald-400" />
          live
        </span>
      );
    }

    if (connectionStatus === "reconnecting") {
      return <span className={`${base} bg-surface-container-low text-amber-700`}>reconnecting</span>;
    }

    if (connectionStatus === "disconnected") {
      return <span className={`${base} bg-surface-container-low text-rose-700`}>disconnected</span>;
    }

    return <span className={`${base} bg-surface-container-low text-on-surface-variant`}>connecting</span>;
  }, [connectionStatus]);

  return (
    <section className="glass-card-strong overflow-hidden rounded-[32px] px-5 py-5 sm:px-6 sm:py-6">
      <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-[0.4em] text-on-surface-variant">Conviction meter</p>
          <div className="mt-2 flex items-center gap-3">
            <h2 className="font-display text-4xl text-on-surface sm:text-5xl">Current consensus</h2>
            {statusPill}
          </div>
          <p className="mt-2 text-sm text-on-surface-variant">Round {currentRound || 0} updates only when ConvictionUpdated arrives from the chain.</p>
        </div>
        <div className="text-right text-sm text-slate-600">
          <p className="uppercase tracking-[0.35em] text-slate-400">Threshold</p>
              <p className="mt-2 font-mono text-lg text-slate-900">{WIN_THRESHOLD} points</p>
        </div>
      </div>

      <div className="mb-4 grid grid-cols-2 gap-4 text-center">
        <div className={`rounded-[24px] bg-surface p-4 ${leader === "bull" ? "lead-pulse" : ""}`}>
          <p className="text-xs uppercase tracking-[0.35em] text-secondary">Bull score</p>
          <p className="font-display text-5xl text-secondary sm:text-6xl">{currentBullScore}</p>
        </div>
        <div className={`rounded-[24px] bg-surface p-4 ${leader === "bear" ? "lead-pulse" : ""}`}>
          <p className="text-xs uppercase tracking-[0.35em] text-tertiary">Bear score</p>
          <p className="font-display text-5xl text-tertiary sm:text-6xl">{currentBearScore}</p>
        </div>
      </div>

      <div key={flashKey} className={`glass-card rounded-[28px] p-2 ${flashKey > 0 ? "meter-flash" : ""}`}>
        <div className="flex h-14 overflow-hidden rounded-[22px] bg-surface-container-low sm:h-16">
          <div
            className={`flex items-center justify-end px-4 text-sm font-semibold text-on-surface transition-[width] duration-700 ease-in-out ${leader === "bull" ? "lead-pulse" : ""}`}
            style={{ width: `${bullPercent}%`, background: 'linear-gradient(135deg, rgba(134,79,81,0.95) 0%, rgba(162,103,105,0.95) 100%)' }}
          >
            <span className="hidden sm:inline">{bullPercent.toFixed(0)}%</span>
          </div>
          <div
            className={`flex items-center justify-start px-4 text-sm font-semibold text-on-surface transition-[width] duration-700 ease-in-out ${leader === "bear" ? "lead-pulse" : ""}`}
            style={{ width: `${bearPercent}%`, background: 'linear-gradient(135deg, rgba(141,72,97,0.95) 0%, rgba(109,87,81,0.95) 100%)' }}
          >
            <span className="hidden sm:inline">{bearPercent.toFixed(0)}%</span>
          </div>
        </div>
      </div>

      <div className="mt-5 grid gap-4 sm:grid-cols-[1fr_auto_1fr] sm:items-center">
        <div className="rounded-[20px] bg-surface p-4 text-sm text-on-surface-variant">
          Bull leads by <span className="font-mono text-on-surface">{Math.max(0, currentBullScore - currentBearScore)}</span> point(s)
        </div>
        <div className="text-center text-sm text-slate-500">live update only, no polling interval</div>
        <div className="rounded-[20px] bg-surface p-4 text-sm text-on-surface-variant">
          Win progress
          <div className="mt-2 h-2 overflow-hidden rounded-full bg-surface-container-low">
            <div className="h-full rounded-full" style={{ width: `${progressPercent}%`, background: 'linear-gradient(135deg, rgba(255,196,170,0.9) 0%, rgba(255,188,166,0.9) 100%)' }} />
          </div>
        </div>
      </div>
    </section>
  );
}
