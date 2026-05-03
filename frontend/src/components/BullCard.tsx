import React from "react";

interface AgentCardProps {
  name: string;
  argument: string;
  confidence: number;
  score: number;
  metrics: string[];
  isActive?: boolean;
}

export function BullCard({ name, argument, confidence, score, metrics, isActive }: AgentCardProps) {
  return (
    <div className={`tonal-card flex flex-col p-8 sm:p-10 ${isActive ? 'agent-speaking bg-surface-container-high scale-[1.01]' : ''}`}>
      <div className="mb-6 flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-12 w-12 items-center justify-center bg-bull-500/10 text-2xl text-bull-500">🐂</div>
          <div>
            <h2 className="headline-md text-bull-500">{name}</h2>
            <div className="flex items-center gap-2 mt-1">
              <span className="label-md text-on-surface-variant">Agent • Off-Chain</span>
              {isActive && <span className="live-dot scale-75" style={{ backgroundColor: '#2d8a63', borderColor: '#2d8a63' }} />}
            </div>
          </div>
        </div>
        <div className="text-right">
          <p className="display-lg text-on-surface">{score}</p>
          <p className="label-md text-on-surface-variant">Score</p>
        </div>
      </div>

      <div className="mb-8 flex-1">
        <p className="body-lg text-on-surface border-l-2 border-outline-variant pl-4">
          {argument}
        </p>
      </div>

      <div className="mt-auto border-t border-outline-variant pt-6">
        <div className="flex flex-wrap gap-3">
          {metrics.map((m, i) => (
            <span key={i} className="bg-surface px-3 py-1 label-md text-on-surface-variant">
              {m}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}
