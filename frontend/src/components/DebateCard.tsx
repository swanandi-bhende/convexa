'use client';

import React, { useState } from 'react';

export type RoundSummary = {
  roundNumber: number;
  winner?: 'bull' | 'bear' | 'tie';
  bullScore?: number;
  bearScore?: number;
  summary?: string;
};

export type DebateSummary = {
  id: string;
  tokenPair: string;
  winner?: 'bull' | 'bear' | 'tie';
  bullScore: number;
  bearScore: number;
  date: string; // ISO
  durationSeconds?: number;
  rounds?: RoundSummary[];
};

interface DebateCardProps {
  debate: DebateSummary;
  onViewDetail?: (id: string) => void;
}

export const DebateCard: React.FC<DebateCardProps> = ({ debate, onViewDetail }) => {
  const [open, setOpen] = useState(false);

  const duration = debate.durationSeconds ? `${Math.floor(debate.durationSeconds/60)}m ${debate.durationSeconds%60}s` : '—';

  return (
    <div className="rounded-lg border border-border-light bg-white overflow-hidden">
      <div className="flex items-center justify-between p-md">
        <div className="flex items-center gap-md">
          <div className="font-semibold text-text-primary">{debate.tokenPair}</div>
          <div className="text-xs text-text-secondary">{new Date(debate.date).toLocaleString()}</div>
        </div>

        <div className="flex items-center gap-md">
          <div className="text-sm text-text-secondary">Winner</div>
          <div className={`px-sm py-xs rounded-md font-semibold ${debate.winner === 'bull' ? 'bg-bull-50 text-bull-600' : debate.winner === 'bear' ? 'bg-bear-50 text-bear-600' : 'bg-surface text-text-secondary'}`}>
            {debate.winner ? debate.winner.toUpperCase() : '—'}
          </div>

          <div className="text-right">
            <div className="text-xs text-text-secondary">Scores</div>
            <div className="font-mono font-semibold">{debate.bullScore} — {debate.bearScore}</div>
          </div>

          <div className="text-xs text-text-secondary">{duration}</div>

          <button
            onClick={() => setOpen(o => !o)}
            className="ml-sm text-sm text-primary hover:underline"
          >
            {open ? 'Hide' : 'Expand'}
          </button>

          <button
            onClick={() => onViewDetail?.(debate.id)}
            className="ml-md px-sm py-xs bg-bull-500 text-white rounded-md text-sm hover:brightness-95"
          >
            View
          </button>
        </div>
      </div>

      {open && (
        <div className="border-t border-border-light bg-surface p-md">
          <h4 className="font-semibold mb-sm">Round Summaries</h4>
          <div className="space-y-sm">
            {(debate.rounds || []).map(r => (
              <div key={r.roundNumber} className="p-sm rounded-md bg-white border border-border-light">
                <div className="flex items-center justify-between">
                  <div className="font-medium">Round {r.roundNumber}</div>
                  <div className="text-sm text-text-secondary">{r.winner ? r.winner.toUpperCase() : '—'}</div>
                </div>
                <div className="mt-sm text-sm text-text-secondary">Scores: {r.bullScore ?? '—'} — {r.bearScore ?? '—'}</div>
                {r.summary && <div className="mt-sm text-sm">{r.summary}</div>}
              </div>
            ))}
            {(!debate.rounds || debate.rounds.length === 0) && (
              <div className="text-text-secondary">No round data available.</div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default DebateCard;
