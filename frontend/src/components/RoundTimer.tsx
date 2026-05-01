'use client';

import React, { useState, useEffect } from 'react';

interface RoundTimerProps {
  currentRound: number;
  totalRounds: number;
  timeRemaining?: number; // in seconds
  status?: 'in-progress' | 'pending' | 'completed';
}

export const RoundTimer: React.FC<RoundTimerProps> = ({
  currentRound,
  totalRounds,
  timeRemaining,
  status = 'in-progress',
}) => {
  const [displayTime, setDisplayTime] = useState(timeRemaining || 0);

  useEffect(() => {
    if (!timeRemaining || status !== 'in-progress') return;

    const timer = setInterval(() => {
      setDisplayTime((prev) => {
        if (prev <= 1) {
          clearInterval(timer);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, [timeRemaining, status]);

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  const progress = (currentRound / totalRounds) * 100;

  const getStatusClasses = () => {
    if (status === 'completed') return 'bg-success-50 text-success-600';
    if (status === 'pending') return 'bg-warning-50 text-warning-600';
    return 'bg-bull-50 text-bull-600';
  };

  const getProgressColor = () => {
    if (status === 'completed') return 'bg-success-500';
    if (status === 'pending') return 'bg-warning-500';
    return 'bg-bull-500';
  };

  const getStatusText = () => {
    if (status === 'completed') return 'Completed';
    if (status === 'pending') return 'Pending';
    return 'In Progress';
  };

  return (
    <div className="rounded-lg border border-border-light bg-white p-lg">
      {/* Header */}
      <div className="mb-lg">
        <div className="flex items-center justify-between mb-md">
          <h3 className="font-semibold text-heading-md text-text-primary">
            Round {currentRound}
            <span className="text-body-md font-normal text-text-secondary ml-md">
              of {totalRounds}
            </span>
          </h3>
          <div className={`px-md py-xs rounded-full font-semibold text-label-sm ${getStatusClasses()}`}>
            {getStatusText()}
          </div>
        </div>

        {/* Progress Bar */}
        <div className="h-2 rounded-full bg-surface-tertiary overflow-hidden">
          <div
            className={`h-full transition-all duration-300 ${getProgressColor()}`}
            style={{
              width: `${progress}%`,
            }}
          />
        </div>
      </div>

      {/* Timer Section */}
      {status === 'in-progress' && timeRemaining !== undefined && (
        <div className="rounded-lg p-lg text-center bg-bull-50">
          <p className="text-label-sm mb-sm text-text-secondary">
            Time Remaining
          </p>
          <p
            className="font-bold tabular-nums"
            style={{
              fontSize: '32px',
              color: 'rgb(37, 99, 235)',
              fontFamily: 'monospace',
            }}
          >
            {formatTime(displayTime)}
          </p>
        </div>
      )}

      {/* Stats */}
      <div className="mt-lg pt-lg border-t border-border-light grid grid-cols-2 gap-md">
        <div>
          <p className="text-label-sm text-text-secondary">
            Rounds Completed
          </p>
          <p className="text-heading-md font-semibold text-text-primary">
            {currentRound - 1}
          </p>
        </div>
        <div>
          <p className="text-label-sm text-text-secondary">
            Remaining
          </p>
          <p className="text-heading-md font-semibold text-text-primary">
            {totalRounds - currentRound}
          </p>
        </div>
      </div>
    </div>
  );
};
