'use client';

import React, { useMemo, useState } from 'react';
import { DebateCard, DebateSummary } from '@/components/DebateCard';
import DebateDetail from '@/components/DebateDetail';

const mockDebates = (): DebateSummary[] => [
  {
    id: 'd-1',
    tokenPair: 'ETH/USDC',
    winner: 'bull',
    bullScore: 510,
    bearScore: 406,
    date: new Date(Date.now() - 1000 * 60 * 60 * 24 * 3).toISOString(),
    durationSeconds: 3600,
    rounds: [
      { roundNumber: 1, winner: 'bull', bullScore: 70, bearScore: 60, summary: 'Bull opened with strong on-chain metrics.' },
      { roundNumber: 2, winner: 'bear', bullScore: 65, bearScore: 70, summary: 'Bear rebuttal focused on macro risks.' },
    ],
  },
  {
    id: 'd-2',
    tokenPair: 'BTC/USDC',
    winner: 'bear',
    bullScore: 420,
    bearScore: 480,
    date: new Date(Date.now() - 1000 * 60 * 60 * 24 * 10).toISOString(),
    durationSeconds: 5400,
    rounds: [
      { roundNumber: 1, winner: 'bear', bullScore: 60, bearScore: 75, summary: 'Bear emphasized regulatory risks.' },
    ],
  },
];

export default function HistoryPage() {
  const debates = useMemo(() => mockDebates(), []);
  const [query, setQuery] = useState('');
  const [tokenFilter, setTokenFilter] = useState<'All' | string>('All');
  const [winnerFilter, setWinnerFilter] = useState<'All' | 'bull' | 'bear' | 'tie'>('All');
  const [dateFrom, setDateFrom] = useState<string | undefined>(undefined);
  const [dateTo, setDateTo] = useState<string | undefined>(undefined);
  const [selected, setSelected] = useState<DebateSummary | null>(null);

  const tokenPairs = useMemo(() => {
    const set = new Set<string>();
    debates.forEach(d => set.add(d.tokenPair));
    return ['All', ...Array.from(set)];
  }, [debates]);

  const filtered = useMemo(() => {
    return debates.filter(d => {
      if (tokenFilter !== 'All' && d.tokenPair !== tokenFilter) return false;
      if (winnerFilter !== 'All' && d.winner !== winnerFilter) return false;
      if (dateFrom && new Date(d.date) < new Date(dateFrom)) return false;
      if (dateTo && new Date(d.date) > new Date(dateTo)) return false;
      if (query) {
        const q = query.toLowerCase();
        if (!d.tokenPair.toLowerCase().includes(q) && !(d.rounds || []).some(r => (r.summary || '').toLowerCase().includes(q))) return false;
      }
      return true;
    });
  }, [debates, tokenFilter, winnerFilter, dateFrom, dateTo, query]);

  return (
    <main className="space-y-lg p-lg">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-heading-lg font-bold">Debate History & Archives</h1>
          <p className="text-text-secondary">Browse past debates, view transcripts and judge verdicts.</p>
        </div>

        <div className="flex items-center gap-md">
          <input
            placeholder="Search token pair or transcript..."
            value={query}
            onChange={e => setQuery(e.target.value)}
            className="px-md py-sm border rounded-md"
          />
          <select value={tokenFilter} onChange={e => setTokenFilter(e.target.value)} className="px-md py-sm border rounded-md">
            {tokenPairs.map(tp => <option key={tp} value={tp}>{tp}</option>)}
          </select>
          <select value={winnerFilter} onChange={e => setWinnerFilter(e.target.value as any)} className="px-md py-sm border rounded-md">
            <option value="All">All</option>
            <option value="bull">Bull</option>
            <option value="bear">Bear</option>
            <option value="tie">Tie</option>
          </select>
          <input type="date" value={dateFrom ?? ''} onChange={e => setDateFrom(e.target.value || undefined)} className="px-md py-sm border rounded-md" />
          <input type="date" value={dateTo ?? ''} onChange={e => setDateTo(e.target.value || undefined)} className="px-md py-sm border rounded-md" />
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-lg">
        <div className="lg:col-span-2 space-y-md">
          {filtered.map(d => (
            <DebateCard key={d.id} debate={d} onViewDetail={(id) => {
              const found = debates.find(x => x.id === id) || null;
              setSelected(found);
            }} />
          ))}
          {filtered.length === 0 && (
            <div className="rounded-lg border border-border-light bg-surface p-lg text-text-secondary">No debates found.</div>
          )}
        </div>

        <div className="lg:col-span-1">
          {selected ? (
            <DebateDetail debate={selected} onClose={() => setSelected(null)} />
          ) : (
            <div className="rounded-lg border border-border-light bg-white p-lg text-text-secondary">Select a debate to see details.</div>
          )}
        </div>
      </div>
    </main>
  );
}
