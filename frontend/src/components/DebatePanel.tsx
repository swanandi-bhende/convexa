"use client";

import React, { useEffect, useMemo, useState } from "react";
import { formatTimestamp } from "@/lib/format";
import { useDebateStore } from "@/store/debateStore";

interface DebatePanelProps {
  side: "bull" | "bear";
}

function buildKeyMetrics(side: "bull" | "bear", bullScore: number, bearScore: number, stakeTotal: string) {
  const lead = side === "bull" ? bullScore - bearScore : bearScore - bullScore;
  return [
    side === "bull" ? `Bull ${bullScore}` : `Bear ${bearScore}`,
    lead >= 0 ? `Lead +${lead}` : `Gap ${Math.abs(lead)}`,
    `${stakeTotal} ETH staked`,
  ];
}

export function DebatePanel({ side }: DebatePanelProps) {
  const { state } = useDebateStore();
  const isBull = side === "bull";
  const argument = isBull ? state.bullArgument : state.bearArgument;
  const score = isBull ? state.currentBullScore : state.currentBearScore;
  const opposingScore = isBull ? state.currentBearScore : state.currentBullScore;
  const stakeTotal = isBull ? state.bullStakeTotal : state.bearStakeTotal;
  const [displayText, setDisplayText] = useState(argument);
  const [highlightKey, setHighlightKey] = useState(0);
  const [typing, setTyping] = useState(false);

  useEffect(() => {
    setHighlightKey((value) => value + 1);
    setTyping(true);
    setDisplayText("");

    let index = 0;
    const interval = window.setInterval(() => {
      index += 1;
      setDisplayText(argument.slice(0, index));

      if (index >= argument.length) {
        window.clearInterval(interval);
        setTyping(false);
      }
    }, 33);

    return () => {
      window.clearInterval(interval);
    };
  }, [argument]);

  const roundEntry = useMemo(() => {
    return state.roundHistory.find((round) => round.roundNumber === state.currentRound) ?? state.roundHistory[0];
  }, [state.currentRound, state.roundHistory]);

  const scoreTone = score >= 60 ? "bg-surface text-emerald-700" : score >= 40 ? "bg-surface text-amber-700" : "bg-surface text-rose-700";
  const panelAnimation = isBull ? "panel-highlight-bull" : "panel-highlight-bear";
  const sectionColor = isBull ? "from-primary/18 via-primary-container/8 to-transparent" : "from-secondary/18 via-tertiary/8 to-transparent";
  const headerColor = isBull ? "editorial-gradient" : "bg-linear-to-r from-secondary to-tertiary";
  const label = isBull ? "Bull" : "Bear";
  const emoji = isBull ? "🐂" : "🐻";
  const keyMetrics = buildKeyMetrics(side, state.currentBullScore, state.currentBearScore, stakeTotal);
  const timestampLabel = roundEntry ? formatTimestamp(roundEntry.timestamp) : "Awaiting first round";

  return (
    <section key={highlightKey} className={`glass-card-strong overflow-hidden rounded-4xl ${highlightKey > 0 ? panelAnimation : ""}`}>
      <div className={`${headerColor} px-5 py-4 sm:px-6`}>
        <div className="flex items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-3 text-on-primary">
              <span className="text-2xl sm:text-3xl">{emoji}</span>
              <div>
                <p className="text-xs uppercase tracking-[0.35em] text-on-primary/75">{label} debate panel</p>
                <h3 className="font-display text-4xl sm:text-5xl">{label}</h3>
              </div>
            </div>
            <p className="mt-3 max-w-lg text-sm text-on-primary/80">The current argument and score update when the chain emits a new ConvictionUpdated event.</p>
          </div>

          <div className="rounded-[18px] bg-surface/95 px-4 py-3 text-right text-on-surface">
            <p className="text-[10px] uppercase tracking-[0.4em] text-on-surface-variant">Confidence</p>
            <p className="font-display text-4xl sm:text-5xl">{score}</p>
            <p className="text-xs uppercase tracking-[0.3em] text-on-surface-variant">of {score + opposingScore}</p>
          </div>
        </div>
      </div>

      <div className={`bg-linear-to-br ${sectionColor} px-5 py-5 sm:px-6 sm:py-6`}>
        <div className="rounded-3xl bg-surface p-5 sm:p-6">
          <p className="text-xs uppercase tracking-[0.35em] text-on-surface-variant">Round {state.currentRound || 0} argument</p>
          <p className="mt-2 min-h-36 text-lg leading-8 text-on-surface sm:text-[1.08rem]">
            {displayText}
            {typing ? <span className="typewriter-caret align-middle text-current" /> : null}
          </p>
        </div>

        <div className="mt-5 flex flex-wrap gap-2">
          {keyMetrics.map((metric) => (
            <span key={metric} className="rounded-full bg-surface-container-low px-3 py-1 text-xs uppercase tracking-[0.25em] text-on-surface-variant">
              {metric}
            </span>
          ))}
        </div>

        <div className="mt-5 flex flex-wrap items-center justify-between gap-3 pt-4 text-sm text-on-surface-variant">
          <span>{roundEntry ? `Round ${roundEntry.roundNumber} argument` : "Awaiting round data"}</span>
          <span className={`rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-[0.35em] ${scoreTone}`}>Judge score {score}</span>
          <span>{timestampLabel}</span>
        </div>
      </div>
    </section>
  );
}
