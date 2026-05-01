'use client';

import React from 'react';

/**
 * Active Debates page - shows currently running debates
 */
export default function ActiveDebatesPage() {
  return (
    <div className="space-y-lg">
      <div className="space-y-md">
        <h1 className="text-display-md font-bold text-text-primary">
          Active Debates
        </h1>
        <p className="text-body-lg text-text-secondary">
          Real-time debates between Bull and Bear agents
        </p>
      </div>

      <div className="rounded-lg border border-border-light bg-surface p-xl">
        <p className="text-center text-body-md text-text-tertiary py-2xl">
          Debate viewer coming in Step 4. View live arguments, confidence scores, and judge verdicts.
        </p>
      </div>
    </div>
  );
}
