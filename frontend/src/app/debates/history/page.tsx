'use client';

import React from 'react';

/**
 * Debate History page - shows past debates and their outcomes
 */
export default function DebateHistoryPage() {
  return (
    <div className="space-y-lg">
      <div className="space-y-md">
        <h1 className="text-display-md font-bold text-text-primary">
          Debate History
        </h1>
        <p className="text-body-lg text-text-secondary">
          Archive of completed debates with outcomes and accuracy metrics
        </p>
      </div>

      <div className="rounded-lg border border-border-light bg-surface p-xl">
        <p className="text-center text-body-md text-text-tertiary py-2xl">
          Debate history archive coming in Step 8. Filter by token pair, winner, and date range.
        </p>
      </div>
    </div>
  );
}
