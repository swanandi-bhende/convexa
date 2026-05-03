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

  const panelAnimation = isBull ? "panel-highlight-bull" : "panel-highlight-bear";
  const label = isBull ? "Bull" : "Bear";
  const emoji = isBull ? "🐂" : "🐻";
  const keyMetrics = buildKeyMetrics(side, state.currentBullScore, state.currentBearScore, stakeTotal);
  const timestampLabel = roundEntry ? formatTimestamp(roundEntry.timestamp) : "Awaiting first round";
  const accentColor = isBull ? "text-bull-500" : "text-bear-500";
  const accentBg = isBull ? "bg-bull-500/10" : "bg-bear-500/10";

  return (
    <section key={highlightKey} className={`tonal-card overflow-hidden relative ${highlightKey > 0 && typing ? panelAnimation : ""}`}>
      {/* Dynamic Background Glow */}
      <div className={`absolute top-0 right-0 w-64 h-64 ${accentBg} opacity-50 rounded-bl-full pointer-events-none transition-all duration-700`} />

      <div className="relative z-10 px-8 py-8 border-b border-outline-variant">
        <div className="flex items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-4">
              <span className="text-4xl drop-shadow-sm">{emoji}</span>
              <div>
                <div className="flex items-center gap-3 mb-1">
                  <p className="label-md text-on-surface-variant">{label} Agent</p>
                  {typing && <span className="bg-primary/10 px-2 py-0.5 label-md text-primary animate-pulse">Orchestrator: Collecting Argument</span>}
                </div>
                <h3 className={`display-lg ${accentColor}`}>{label}</h3>
              </div>
            </div>
          </div>

          <div className="bg-surface-container-highest px-6 py-4 text-right">
            <p className="label-md text-on-surface-variant">Confidence</p>
            <p className="display-lg text-on-surface">{score}</p>
            <p className="label-md text-on-surface-variant mt-1">out of {score + opposingScore}</p>
          </div>
        </div>
      </div>

      <div className="relative z-10 px-8 py-8 bg-surface">
        <div className={`p-8 bg-surface-container-low transition-all duration-300 ${typing ? 'shadow-inner' : ''}`}>
          <p className="label-md text-secondary mb-4 flex items-center gap-3">
            Round {state.currentRound || 0} argument
            {typing && <span className="w-2 h-2 rounded-full bg-primary animate-pulse" />}
          </p>
          <p className="min-h-[12rem] body-lg text-on-surface">
            {displayText}
            {typing ? <span className="typewriter-caret text-primary" /> : null}
          </p>
        </div>

        <div className="mt-8 flex flex-wrap gap-4">
          {keyMetrics.map((metric) => (
            <span key={metric} className="bg-surface-container-highest px-4 py-2 label-md text-on-surface-variant">
              {metric}
            </span>
          ))}
        </div>

        <div className="mt-8 flex flex-wrap items-center justify-between gap-4 pt-6 border-t border-outline-variant text-sm text-on-surface-variant">
          <span className="flex items-center gap-2 label-md">
            <span className="w-2 h-2 rounded-full bg-on-surface-variant" />
            {roundEntry ? `Round ${roundEntry.roundNumber}` : "Awaiting data"}
          </span>
          <span className={`px-4 py-2 label-md ${accentBg} ${accentColor}`}>
            Judge score: {score}
          </span>
          <span className="font-mono text-xs">{timestampLabel}</span>
        </div>
      </div>
    </section>
  );
}
