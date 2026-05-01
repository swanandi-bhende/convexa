'use client';

import React, { useEffect, useState } from 'react';

interface ConvictionTrackerProps {
  bullScore: number;
  bearScore: number;
  winThreshold?: number;
  animationDuration?: number;
  showThreshold?: boolean;
}

/**
 * Conviction Tracker component showing real-time Bull vs Bear conviction scores
 */
export const ConvictionTracker: React.FC<ConvictionTrackerProps> = ({
  bullScore: initialBullScore,
  bearScore: initialBearScore,
  winThreshold = 70,
  animationDuration = 500,
  showThreshold = true,
}) => {
  const [bullScore, setBullScore] = useState(initialBullScore);
  const [bearScore, setBearScore] = useState(initialBearScore);

  // Animate score changes
  useEffect(() => {
    setBullScore(initialBullScore);
    setBearScore(initialBearScore);
  }, [initialBullScore, initialBearScore]);

  const totalScore = bullScore + bearScore || 100;
  const bullPercentage = totalScore > 0 ? (bullScore / totalScore) * 100 : 50;
  const bearPercentage = totalScore > 0 ? (bearScore / totalScore) * 100 : 50;

  const bullReachedThreshold = bullScore >= winThreshold;
  const bearReachedThreshold = bearScore >= winThreshold;

  return (
    <div className="rounded-lg border border-border-light bg-surface p-lg md:p-xl">
      <div className="space-y-lg">
        {/* Header */}
        <div className="flex items-center justify-between">
          <h3 className="text-heading-lg font-semibold text-text-primary">
            Conviction Tracker
          </h3>
          {bullReachedThreshold && (
            <span className="inline-flex items-center gap-sm rounded-full bg-success-50 px-md py-sm">
              <div className="h-2 w-2 rounded-full bg-success-500" />
              <span className="text-label-md font-semibold text-success-500">
                Bull Win
              </span>
            </span>
          )}
          {bearReachedThreshold && (
            <span className="inline-flex items-center gap-sm rounded-full bg-warning-50 px-md py-sm">
              <div className="h-2 w-2 rounded-full bg-warning-500" />
              <span className="text-label-md font-semibold text-warning-500">
                Bear Win
              </span>
            </span>
          )}
        </div>

        {/* Main Conviction Bar */}
        <div className="space-y-md">
          {/* Score Display */}
          <div className="flex items-end justify-between">
            <div className="text-center flex-1">
              <p className="text-heading-md font-semibold text-bull-primary">
                {bullScore}
              </p>
              <p className="text-body-sm text-text-secondary">Bull</p>
            </div>
            <div className="flex-1 px-md">
              <div className="flex items-center justify-center h-12">
                <div className="text-center">
                  <p className="text-body-sm text-text-tertiary">Conviction Score</p>
                </div>
              </div>
            </div>
            <div className="text-center flex-1">
              <p className="text-heading-md font-semibold text-bear-primary">
                {bearScore}
              </p>
              <p className="text-body-sm text-text-secondary">Bear</p>
            </div>
          </div>

          {/* Conviction Bar */}
          <div className="h-8 w-full overflow-hidden rounded-full bg-border-light flex">
            {/* Bull Side */}
            <div
              className="bg-bull-500 transition-all duration-500 flex items-center justify-center"
              style={{ width: `${bullPercentage}%` }}
            >
              {bullPercentage > 15 && (
                <span className="text-xs font-semibold text-text-inverted">
                  {Math.round(bullPercentage)}%
                </span>
              )}
            </div>

            {/* Bear Side */}
            <div
              className="bg-bear-500 transition-all duration-500 flex items-center justify-center"
              style={{ width: `${bearPercentage}%` }}
            >
              {bearPercentage > 15 && (
                <span className="text-xs font-semibold text-text-inverted">
                  {Math.round(bearPercentage)}%
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Threshold Indicator */}
        {showThreshold && (
          <div className="space-y-sm">
            <div className="flex items-center justify-between text-body-sm">
              <span className="text-text-tertiary">Win Threshold</span>
              <span className="font-semibold text-text-primary">{winThreshold}</span>
            </div>
            <div className="h-1 w-full bg-border-light rounded-full overflow-hidden">
              <div
                className="h-full bg-info-500 transition-all"
                style={{
                  width: `${(winThreshold / 100) * 100}%`,
                }}
              />
            </div>
          </div>
        )}

        {/* Status Message */}
        <div className="flex items-center justify-center gap-lg pt-md border-t border-border-light">
          <div className="flex flex-col items-center gap-xs flex-1">
            <p className="text-label-sm font-semibold text-text-primary">
              {bullScore > bearScore
                ? 'Bull Advantage'
                : bearScore > bullScore
                ? 'Bear Advantage'
                : 'Tied'}
            </p>
            <p className="text-body-sm text-text-secondary">
              Difference: {Math.abs(bullScore - bearScore)}
            </p>
          </div>
          <div className="h-8 w-px bg-border-light" />
          <div className="flex flex-col items-center gap-xs flex-1">
            <p className="text-label-sm font-semibold text-text-primary">
              {bullReachedThreshold || bearReachedThreshold ? 'Round Complete' : 'In Progress'}
            </p>
            <p className="text-body-sm text-text-secondary">
              {bullScore + bearScore > 0
                ? `Combined: ${bullScore + bearScore}`
                : 'Awaiting verdicts'}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
