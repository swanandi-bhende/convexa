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
    if (connectionStatus === "live") {
      return (
        <span className="inline-flex items-center gap-2 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-3 py-1 text-xs font-semibold uppercase tracking-[0.3em] text-emerald-200">
          <span className="live-dot inline-block h-2 w-2 rounded-full bg-emerald-300" />
          live
        </span>
      );
    }

    if (connectionStatus === "reconnecting") {
      return (
        <span className="inline-flex items-center gap-2 rounded-full border border-amber-500/30 bg-amber-500/10 px-3 py-1 text-xs font-semibold uppercase tracking-[0.3em] text-amber-200">
          reconnecting
        </span>
      );
    }

    if (connectionStatus === "disconnected") {
      return (
        <span className="inline-flex items-center gap-2 rounded-full border border-rose-500/30 bg-rose-500/10 px-3 py-1 text-xs font-semibold uppercase tracking-[0.3em] text-rose-200">
          disconnected
        </span>
      );
    }

    return (
      <span className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs font-semibold uppercase tracking-[0.3em] text-white/70">
        connecting
      </span>
    );
  }, [connectionStatus]);

  return (
    <section className="glass-card-strong overflow-hidden rounded-[32px] px-5 py-5 shadow-[0_22px_60px_rgba(60,48,36,0.1)] sm:px-6 sm:py-6">
      <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-[0.4em] text-slate-500">Conviction meter</p>
          <div className="mt-2 flex items-center gap-3">
            <h2 className="font-display text-4xl text-slate-900 sm:text-5xl">Current consensus</h2>
            {statusPill}
          </div>
          <p className="mt-2 text-sm text-slate-600">Round {currentRound || 0} updates only when ConvictionUpdated arrives from the chain.</p>
        </div>
        <div className="text-right text-sm text-slate-600">
          <p className="uppercase tracking-[0.35em] text-slate-400">Threshold</p>
              <p className="mt-2 font-mono text-lg text-slate-900">{WIN_THRESHOLD} points</p>
        </div>
      </div>

      <div className="mb-4 grid grid-cols-2 gap-4 text-center">
        <div className={`rounded-[24px] border border-emerald-300/30 bg-emerald-50 px-4 py-5 ${leader === "bull" ? "lead-pulse" : ""}`}>
          <p className="text-xs uppercase tracking-[0.35em] text-emerald-700">Bull score</p>
          <p className="font-display text-5xl text-emerald-700 sm:text-6xl">{currentBullScore}</p>
        </div>
        <div className={`rounded-[24px] border border-rose-300/30 bg-rose-50 px-4 py-5 ${leader === "bear" ? "lead-pulse" : ""}`}>
          <p className="text-xs uppercase tracking-[0.35em] text-rose-700">Bear score</p>
          <p className="font-display text-5xl text-rose-700 sm:text-6xl">{currentBearScore}</p>
        </div>
      </div>

      <div key={flashKey} className={`glass-card rounded-[28px] p-2 ${flashKey > 0 ? "meter-flash" : ""}`}>
        <div className="flex h-14 overflow-hidden rounded-[22px] bg-slate-100 sm:h-16">
          <div
            className={`flex items-center justify-end bg-linear-to-r from-emerald-500 via-emerald-400 to-emerald-300 px-4 text-sm font-semibold text-emerald-950 transition-[width] duration-700 ease-in-out ${leader === "bull" ? "lead-pulse" : ""}`}
            style={{ width: `${bullPercent}%` }}
          >
            <span className="hidden sm:inline text-emerald-950">{bullPercent.toFixed(0)}%</span>
          </div>
          <div
            className={`flex items-center justify-start bg-linear-to-r from-rose-300 via-rose-400 to-rose-500 px-4 text-sm font-semibold text-rose-950 transition-[width] duration-700 ease-in-out ${leader === "bear" ? "lead-pulse" : ""}`}
            style={{ width: `${bearPercent}%` }}
          >
            <span className="hidden sm:inline text-rose-950">{bearPercent.toFixed(0)}%</span>
          </div>
        </div>
      </div>

      <div className="mt-5 grid gap-4 sm:grid-cols-[1fr_auto_1fr] sm:items-center">
        <div className="rounded-[20px] border border-slate-200 bg-white px-4 py-3 text-sm text-slate-600 shadow-[0_10px_30px_rgba(60,48,36,0.05)]">
          Bull leads by <span className="font-mono text-slate-900">{Math.max(0, currentBullScore - currentBearScore)}</span> point(s)
        </div>
        <div className="text-center text-sm text-slate-500">live update only, no polling interval</div>
        <div className="rounded-[20px] border border-slate-200 bg-white px-4 py-3 text-sm text-slate-600 shadow-[0_10px_30px_rgba(60,48,36,0.05)]">
          Win progress
          <div className="mt-2 h-2 overflow-hidden rounded-full bg-slate-100">
            <div className="h-full rounded-full bg-linear-to-r from-amber-300 via-amber-400 to-amber-500 transition-[width] duration-700 ease-in-out" style={{ width: `${progressPercent}%` }} />
          </div>
        </div>
      </div>
    </section>
  );
}
