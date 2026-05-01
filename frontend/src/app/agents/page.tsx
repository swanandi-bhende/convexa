'use client';

import React from 'react';

/**
 * Agent Stats page - shows performance metrics for Bull and Bear agents
 */
export default function AgentStatsPage() {
  return (
    <div className="space-y-lg">
      <div className="space-y-md">
        <h1 className="text-display-md font-bold text-text-primary">
          Agent Performance
        </h1>
        <p className="text-body-lg text-text-secondary">
          Bull and Bear agent statistics, accuracy metrics, and leaderboards
        </p>
      </div>

      <div className="rounded-lg border border-border-light bg-surface p-xl">
        <p className="text-center text-body-md text-text-tertiary py-2xl">
          Agent performance dashboard coming in Step 7. View accuracy rates, debate wins, and key metrics.
        </p>
      </div>
    </div>
  );
}
