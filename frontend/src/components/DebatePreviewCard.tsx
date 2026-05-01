'use client';

import React from 'react';
import Link from 'next/link';

interface DebatePreviewCardProps {
  id: number;
  tokenPair: string;
  round: number;
  totalRounds: number;
  bullScore: number;
  bearScore: number;
  status: 'in-progress' | 'pending' | 'completed';
  bullArgument?: string;
  bearArgument?: string;
  bullConfidence?: number;
  bearConfidence?: number;
}

/**
 * Debate Preview Card for showing debate summaries
 */
export const DebatePreviewCard: React.FC<DebatePreviewCardProps> = ({
  id,
  tokenPair,
  round,
  totalRounds,
  bullScore,
  bearScore,
  status,
  bullArgument,
  bearArgument,
  bullConfidence,
  bearConfidence,
}) => {
  const isCompleted = status === 'completed';
  const isInProgress = status === 'in-progress';
  const leader = bullScore > bearScore ? 'bull' : bullScore < bearScore ? 'bear' : 'tied';

  const statusConfig = {
    'in-progress': { color: 'success-50', textColor: 'success-500', label: 'Live' },
    'pending': { color: 'warning-50', textColor: 'warning-500', label: 'Pending' },
    'completed': { color: 'surface-tertiary', textColor: 'text-secondary', label: 'Completed' },
  };

  const config = statusConfig[status];

  return (
    <Link href={`/debates/${isCompleted ? 'history' : 'active'}/${id}`}>
      <div className="rounded-lg border border-border-light bg-surface p-lg transition-all duration-200 hover:shadow-lg cursor-pointer">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <p className="text-label-lg font-semibold text-text-primary">
              {tokenPair}
            </p>
            <p className="text-body-sm text-text-secondary">
              Round {round} of {totalRounds}
            </p>
          </div>
          <span
            className={`inline-flex rounded-full bg-${config.color} px-md py-sm text-label-md font-semibold text-${config.textColor}`}
          >
            {config.label}
          </span>
        </div>

        {/* Arguments (if provided) */}
        {bullArgument && bearArgument && (
          <div className="mt-lg grid grid-cols-1 gap-md md:grid-cols-2">
            {/* Bull Argument */}
            <div className="rounded-md bg-bull-50 border border-bull-500 border-opacity-20 p-md">
              <div className="flex items-center justify-between mb-sm">
                <p className="text-label-md font-semibold text-bull-primary">
                  Bull Position
                </p>
                {bullConfidence !== undefined && (
                  <span className="text-body-sm font-semibold text-bull-primary">
                    {bullConfidence}%
                  </span>
                )}
              </div>
              <p className="text-body-sm text-text-secondary line-clamp-2">
                {bullArgument}
              </p>
            </div>

            {/* Bear Argument */}
            <div className="rounded-md bg-bear-50 border border-bear-500 border-opacity-20 p-md">
              <div className="flex items-center justify-between mb-sm">
                <p className="text-label-md font-semibold text-bear-primary">
                  Bear Position
                </p>
                {bearConfidence !== undefined && (
                  <span className="text-body-sm font-semibold text-bear-primary">
                    {bearConfidence}%
                  </span>
                )}
              </div>
              <p className="text-body-sm text-text-secondary line-clamp-2">
                {bearArgument}
              </p>
            </div>
          </div>
        )}

        {/* Score Bars */}
        <div className="mt-lg space-y-lg">
          {/* Bull Score */}
          <div className="space-y-sm">
            <div className="flex items-center justify-between">
              <p className="text-label-md font-semibold text-bull-primary">
                Bull Conviction
              </p>
              <p className="text-label-md font-semibold text-text-primary">
                {bullScore}
              </p>
            </div>
            <div className="h-2.5 w-full overflow-hidden rounded-full bg-border-light">
              <div
                className="h-full bg-bull-500 transition-all duration-500"
                style={{ width: `${bullScore}%` }}
              />
            </div>
          </div>

          {/* Bear Score */}
          <div className="space-y-sm">
            <div className="flex items-center justify-between">
              <p className="text-label-md font-semibold text-bear-primary">
                Bear Conviction
              </p>
              <p className="text-label-md font-semibold text-text-primary">
                {bearScore}
              </p>
            </div>
            <div className="h-2.5 w-full overflow-hidden rounded-full bg-border-light">
              <div
                className="h-full bg-bear-500 transition-all duration-500"
                style={{ width: `${bearScore}%` }}
              />
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="mt-lg flex items-center justify-between pt-lg border-t border-border-light">
          <p className="text-body-sm text-text-tertiary">
            {leader === 'bull'
              ? 'Bull leading'
              : leader === 'bear'
              ? 'Bear leading'
              : 'Tied'}
          </p>
          <p className="text-label-md font-semibold text-bull-500 group-hover:translate-x-xs transition-transform">
            View Details →
          </p>
        </div>
      </div>
    </Link>
  );
};
