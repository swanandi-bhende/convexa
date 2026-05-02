'use client';

import React, { Suspense } from 'react';
const Sparkline = React.lazy(() => import('./_Sparkline'));
import { AgentSummary } from './AgentLeaderboard';

interface AgentStatsProps {
  agent: AgentSummary;
  accuracySeries?: number[]; // last N rounds accuracy 0-100
  onBack?: () => void;
}

export const AgentStats: React.FC<AgentStatsProps> = ({ agent, accuracySeries = [], onBack }) => {
  const width = 480;
  const height = 80;

  // normalize series to SVG points
  const points = (accuracySeries.length > 0 ? accuracySeries : [agent.accuracyRate]).map((v, i, arr) => {
    const x = (i / Math.max(1, arr.length - 1)) * width;
    const y = height - (v / 100) * height;
    return `${x},${y}`;
  }).join(' ');

  return (
    <div className="rounded-lg border border-border-light bg-white p-lg">
      <div className="flex items-start justify-between">
        <div>
          <button className="text-sm text-text-secondary mb-sm" onClick={onBack}>← Back</button>
          <h3 className="text-heading-md font-semibold">{agent.name}</h3>
          <p className="text-xs text-text-secondary">Avg Confidence: <span className="font-medium">{agent.avgConfidence.toFixed(1)}%</span></p>
        </div>
        <div className="text-right">
          <div className="text-sm text-text-secondary">Lifetime Wins</div>
          <div className="text-lg font-bold">{agent.lifetimeWins}</div>
        </div>
      </div>

      <div className="mt-md">
        <div className="text-sm text-text-secondary mb-sm">Accuracy (last {accuracySeries.length || 1} rounds)</div>
        <div className="w-full overflow-hidden">
          <Suspense fallback={<div className="h-20 w-full bg-surface" aria-hidden />}> 
            <Sparkline points={points} color={agent.side === 'bull' ? '#0ea5e9' : '#fb923c'} width={width} height={height} />
          </Suspense>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-md mt-lg">
        <div className="rounded-md p-sm bg-surface">
          <div className="text-xs text-text-secondary">Accuracy Rate</div>
          <div className="text-lg font-semibold">{agent.accuracyRate.toFixed(1)}%</div>
        </div>
        <div className="rounded-md p-sm bg-surface">
          <div className="text-xs text-text-secondary">Avg Confidence</div>
          <div className="text-lg font-semibold">{agent.avgConfidence.toFixed(1)}%</div>
        </div>
        <div className="rounded-md p-sm bg-surface">
          <div className="text-xs text-text-secondary">Key Metric Accuracy</div>
          <div className="text-lg font-semibold">{agent.keyMetricAccuracy.toFixed(1)}%</div>
        </div>
        <div className="rounded-md p-sm bg-surface">
          <div className="text-xs text-text-secondary">Rounds</div>
          <div className="text-lg font-semibold">{agent.lifetimeRounds}</div>
        </div>
      </div>
    </div>
  );
};

export default AgentStats;
