'use client';

import React from 'react';

export type AgentSummary = {
  id: string;
  name: string;
  side: 'bull' | 'bear';
  avgConfidence: number; // 0-100
  accuracyRate: number; // 0-100
  lifetimeWins: number;
  lifetimeRounds: number;
  keyMetricAccuracy: number; // 0-100
  tokenPairs?: string[];
};

interface AgentLeaderboardProps {
  agents?: AgentSummary[];
  onSelect?: (agentId: string) => void;
  limit?: number;
}

export const AgentLeaderboard: React.FC<AgentLeaderboardProps> = ({
  agents = [],
  onSelect,
  limit = 10,
}) => {
  const sorted = [...agents].sort((a, b) => b.accuracyRate - a.accuracyRate).slice(0, limit);

  return (
    <div className="rounded-lg border border-border-light bg-white p-lg">
      <div className="flex items-center justify-between mb-md">
        <h3 className="text-heading-md font-semibold">Agent Leaderboard</h3>
        <span className="text-sm text-text-secondary">Top by accuracy</span>
      </div>

      <ul className="space-y-sm">
        {sorted.map((a, idx) => (
          <li
            key={a.id}
            className="flex items-center justify-between p-sm rounded-md hover:bg-surface cursor-pointer"
            onClick={() => onSelect?.(a.id)}
          >
            <div className="flex items-center gap-md">
              <div className="w-10 h-10 rounded-full bg-gray-100 flex items-center justify-center text-lg font-bold text-gray-700">{a.name.charAt(0)}</div>
              <div>
                <div className="font-medium text-text-primary">{a.name}</div>
                <div className="text-xs text-text-secondary">{a.lifetimeWins} wins • {a.lifetimeRounds} rounds</div>
              </div>
            </div>

            <div className="flex items-center gap-md">
              <div className="text-right">
                <div className="text-sm font-semibold text-text-primary">{a.accuracyRate.toFixed(1)}%</div>
                <div className="text-xs text-text-secondary">accuracy</div>
              </div>

              <div className="w-36">
                <div className="h-2 bg-surface rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full ${a.side === 'bull' ? 'bg-bull-500' : 'bg-bear-500'}`}
                    style={{ width: `${Math.min(100, a.accuracyRate)}%` }}
                  />
                </div>
              </div>
            </div>
          </li>
        ))}
      </ul>

      {agents.length === 0 && (
        <div className="text-center text-text-secondary mt-md">No agents yet.</div>
      )}
    </div>
  );
};

export default AgentLeaderboard;
