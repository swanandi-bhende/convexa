'use client';

import React, { useMemo, useState } from 'react';
import AgentLeaderboard from '@/components/AgentLeaderboard';
import AgentStats from '@/components/AgentStats';
import { AgentSummary } from '@/components/AgentLeaderboard';

const mockAgents = (): AgentSummary[] => [
  {
    id: 'bull-1',
    name: 'Bull Agent Alpha',
    side: 'bull',
    avgConfidence: 72.4,
    accuracyRate: 78.2,
    lifetimeWins: 42,
    lifetimeRounds: 58,
    keyMetricAccuracy: 80.1,
    tokenPairs: ['ETH/USDC', 'BTC/USDC'],
  },
  {
    id: 'bear-1',
    name: 'Bear Agent Omega',
    side: 'bear',
    avgConfidence: 65.1,
    accuracyRate: 70.5,
    lifetimeWins: 36,
    lifetimeRounds: 60,
    keyMetricAccuracy: 68.9,
    tokenPairs: ['ETH/USDC'],
  },
  {
    id: 'bull-2',
    name: 'Bull Agent Beta',
    side: 'bull',
    avgConfidence: 59.3,
    accuracyRate: 62.8,
    lifetimeWins: 18,
    lifetimeRounds: 40,
    keyMetricAccuracy: 60.4,
    tokenPairs: ['SOL/USDC'],
  },
];

export default function AgentsPage() {
  const agents = useMemo(() => mockAgents(), []);
  const [selectedAgentId, setSelectedAgentId] = useState<string | null>(agents[0]?.id ?? null);
  const [tokenFilter, setTokenFilter] = useState<string>('All');
  const [dateRange, setDateRange] = useState<{ from?: string; to?: string }>({});

  const filtered = useMemo(() => {
    if (tokenFilter === 'All') return agents;
    return agents.filter(a => (a.tokenPairs || []).includes(tokenFilter));
  }, [agents, tokenFilter]);

  const selectedAgent = agents.find(a => a.id === selectedAgentId) || filtered[0] || null;

  const accuracySeries = useMemo(() => {
    const base = selectedAgent?.accuracyRate ?? 70;
    return Array.from({ length: 12 }).map((_, i) => Math.max(40, Math.min(98, base + (Math.sin(i / 2) * 8) + (Math.random() * 4 - 2))));
  }, [selectedAgent]);

  const tokenPairs = useMemo(() => {
    const set = new Set<string>();
    agents.forEach(a => (a.tokenPairs || []).forEach(t => set.add(t)));
    return ['All', ...Array.from(set)];
  }, [agents]);

  return (
    <main className="space-y-lg p-lg">
      <div className="flex items-center justify-between">
        <h1 className="text-heading-lg font-bold">Agent Performance Dashboard</h1>
        <div className="flex items-center gap-md">
          <select
            value={tokenFilter}
            onChange={(e) => setTokenFilter(e.target.value)}
            className="px-md py-sm border rounded-md"
          >
            {tokenPairs.map(tp => (
              <option key={tp} value={tp}>{tp}</option>
            ))}
          </select>

          <input
            type="date"
            value={dateRange.from ?? ''}
            onChange={(e) => setDateRange(d => ({ ...d, from: e.target.value }))}
            className="px-md py-sm border rounded-md"
          />
          <input
            type="date"
            value={dateRange.to ?? ''}
            onChange={(e) => setDateRange(d => ({ ...d, to: e.target.value }))}
            className="px-md py-sm border rounded-md"
          />
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-lg">
        <div className="lg:col-span-1">
          <AgentLeaderboard
            agents={filtered}
            onSelect={(id) => setSelectedAgentId(id)}
            limit={20}
          />
        </div>

        <div className="lg:col-span-2">
          {selectedAgent ? (
            <AgentStats agent={selectedAgent} accuracySeries={accuracySeries} onBack={() => setSelectedAgentId(null)} />
          ) : (
            <div className="rounded-lg border border-border-light bg-surface p-lg text-text-secondary">Select an agent to view detailed stats.</div>
          )}
        </div>
      </div>
    </main>
  );
}
