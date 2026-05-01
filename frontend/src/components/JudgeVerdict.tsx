'use client';

import React, { useState, useEffect } from 'react';

interface ScoreBreakdown {
  reasoning: string;
  bullScore: number;
  bearScore: number;
}

interface JudgeVerdictProps {
  status: 'pending' | 'revealed';
  tokenPair: string;
  winner?: 'bull' | 'bear' | 'tie';
  scoreBreakdown?: ScoreBreakdown;
  animationDuration?: number;
}

export const JudgeVerdict: React.FC<JudgeVerdictProps> = ({
  status,
  tokenPair,
  winner,
  scoreBreakdown,
  animationDuration = 800,
}) => {
  const [isAnimating, setIsAnimating] = useState(status === 'revealed');
  const [bullScore, setBullScore] = useState(0);
  const [bearScore, setBearScore] = useState(0);

  useEffect(() => {
    if (status === 'revealed' && scoreBreakdown) {
      setIsAnimating(true);
      const steps = 30;
      const interval = animationDuration / steps;
      let currentStep = 0;

      const timer = setInterval(() => {
        currentStep++;
        const progress = currentStep / steps;
        setBullScore(Math.floor(scoreBreakdown.bullScore * progress));
        setBearScore(Math.floor(scoreBreakdown.bearScore * progress));

        if (currentStep >= steps) {
          setBullScore(scoreBreakdown.bullScore);
          setBearScore(scoreBreakdown.bearScore);
          clearInterval(timer);
          setIsAnimating(false);
        }
      }, interval);

      return () => clearInterval(timer);
    }
  }, [status, scoreBreakdown, animationDuration]);

  const getWinnerClass = () => {
    if (winner === 'bull') return 'bg-bull-50 border-bull-200 text-bull-600';
    if (winner === 'bear') return 'bg-bear-50 border-bear-200 text-bear-600';
    return 'bg-success-50 border-success-200 text-success-600';
  };

  const getWinnerText = () => {
    if (winner === 'bull') return 'Bull Wins';
    if (winner === 'bear') return 'Bear Wins';
    return 'Tie';
  };

  return (
    <div className="flex flex-col rounded-lg border-2 border-border-light bg-white overflow-hidden">
      {/* Header */}
      <div className="px-lg py-lg border-b border-border-light bg-bull-50">
        <h3 className="font-semibold mb-sm text-heading-md text-text-primary">
          Judge Verdict
        </h3>
        <p className="text-body-sm text-text-secondary">{tokenPair}</p>
      </div>

      {/* Content */}
      <div className="px-lg py-lg">
        {status === 'pending' ? (
          <div className="flex flex-col items-center justify-center py-2xl gap-lg">
            <div className="flex gap-sm">
              <div
                className="w-2 h-2 rounded-full animate-bounce bg-bull-500"
                style={{ animationDelay: '0ms' }}
              />
              <div
                className="w-2 h-2 rounded-full animate-bounce bg-bear-500"
                style={{ animationDelay: '150ms' }}
              />
              <div
                className="w-2 h-2 rounded-full animate-bounce bg-bull-500"
                style={{ animationDelay: '300ms' }}
              />
            </div>
            <p className="text-body-md text-text-secondary">
              Judge evaluating arguments...
            </p>
          </div>
        ) : (
          <>
            {/* Winner Announcement */}
            <div
              className={`rounded-lg p-lg mb-lg text-center border ${getWinnerClass()}`}
            >
              <p className={`font-semibold text-heading-md`}>
                {getWinnerText()}
              </p>
            </div>

            {/* Score Breakdown */}
            {scoreBreakdown && (
              <>
                <div className="space-y-md mb-lg">
                  {/* Bull Score */}
                  <div>
                    <div className="flex items-center justify-between mb-sm">
                      <span className="text-label-md font-semibold text-bull-600">
                        Bull Score
                      </span>
                      <span className="text-heading-md font-bold text-bull-500">
                        {bullScore}/100
                      </span>
                    </div>
                    <div className="h-3 rounded-full bg-bull-100 overflow-hidden">
                      <div
                        className="h-full transition-all bg-bull-500"
                        style={{
                          width: `${bullScore}%`,
                          transitionDuration: isAnimating
                            ? `${animationDuration}ms`
                            : '0ms',
                        }}
                      />
                    </div>
                  </div>

                  {/* Bear Score */}
                  <div>
                    <div className="flex items-center justify-between mb-sm">
                      <span className="text-label-md font-semibold text-bear-600">
                        Bear Score
                      </span>
                      <span className="text-heading-md font-bold text-bear-500">
                        {bearScore}/100
                      </span>
                    </div>
                    <div className="h-3 rounded-full bg-bear-100 overflow-hidden">
                      <div
                        className="h-full transition-all bg-bear-500"
                        style={{
                          width: `${bearScore}%`,
                          transitionDuration: isAnimating
                            ? `${animationDuration}ms`
                            : '0ms',
                        }}
                      />
                    </div>
                  </div>
                </div>

                {/* Reasoning */}
                {scoreBreakdown.reasoning && (
                  <div className="p-md rounded-lg bg-surface-tertiary">
                    <p className="text-label-sm font-semibold mb-sm text-text-secondary">
                      Reasoning
                    </p>
                    <p className="text-body-sm text-text-primary leading-relaxed">
                      {scoreBreakdown.reasoning}
                    </p>
                  </div>
                )}
              </>
            )}
          </>
        )}
      </div>
    </div>
  );
};
