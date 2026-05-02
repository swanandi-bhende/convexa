'use client';

import React from 'react';
import { DebateSummary } from './DebateCard';

interface DebateDetailProps {
  debate: DebateSummary;
  onClose?: () => void;
}

export const DebateDetail: React.FC<DebateDetailProps> = ({ debate, onClose }) => {
  return (
    <div className="rounded-lg border border-border-light bg-white p-lg">
      <div className="flex items-center justify-between mb-md">
        <div>
          <h2 className="text-heading-md font-semibold">Debate: {debate.tokenPair}</h2>
          <div className="text-xs text-text-secondary">{new Date(debate.date).toLocaleString()}</div>
        </div>
        <div className="flex items-center gap-md">
          <button onClick={onClose} className="text-sm text-text-secondary">Close</button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-lg">
        <div>
          <h4 className="font-semibold mb-sm">Summary</h4>
          <div className="text-sm text-text-secondary mb-md">Winner: <span className="font-medium">{debate.winner ?? '—'}</span></div>
          <div className="text-sm">Final Scores: <span className="font-mono font-semibold">{debate.bullScore} — {debate.bearScore}</span></div>
          <div className="mt-md text-sm text-text-secondary">Duration: {debate.durationSeconds ? `${Math.floor(debate.durationSeconds/60)}m ${debate.durationSeconds%60}s` : '—'}</div>
        </div>

        <div>
          <h4 className="font-semibold mb-sm">Round Transcript</h4>
          <div className="space-y-sm max-h-56 overflow-auto p-sm bg-surface rounded-md">
            {(debate.rounds || []).map(r => (
              <div key={r.roundNumber} className="p-sm border border-border-light rounded-md bg-white">
                <div className="font-medium">Round {r.roundNumber} • {r.winner ? r.winner.toUpperCase() : '—'}</div>
                <div className="text-xs text-text-secondary">Scores: {r.bullScore ?? '—'} — {r.bearScore ?? '—'}</div>
                {r.summary ? <div className="mt-sm text-sm">{r.summary}</div> : <div className="mt-sm text-sm text-text-secondary">No transcript</div>}
              </div>
            ))}
            {(!debate.rounds || debate.rounds.length === 0) && (
              <div className="text-text-secondary">No rounds recorded.</div>
            )}
          </div>
        </div>
      </div>

    </div>
  );
};

export default DebateDetail;
