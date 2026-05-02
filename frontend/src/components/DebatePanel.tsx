'use client';

import React, { useEffect, useState } from 'react';
import { useDebateStore } from '@/store/debateStore';

interface DebatePanelProps {
  side: 'bull' | 'bear';
}

const DebatePanel: React.FC<DebatePanelProps> = ({ side }) => {
  const { state } = useDebateStore();
  const argument = side === 'bull' ? state.bullArgument : state.bearArgument;
  const [displayText, setDisplayText] = useState(argument);
  const [isAnimating, setIsAnimating] = useState(false);

  // Typewriter effect
  useEffect(() => {
    if (argument === displayText) return;

    setIsAnimating(true);
    let index = 0;
    const targetText = argument;

    const interval = setInterval(() => {
      if (index < targetText.length) {
        setDisplayText(targetText.substring(0, index + 1));
        index++;
      } else {
        setIsAnimating(false);
        clearInterval(interval);
      }
    }, 35); // ~30 chars/sec

    return () => clearInterval(interval);
  }, [argument]);

  const isBull = side === 'bull';
  const headerBg = isBull ? 'bg-green-600' : 'bg-red-600';
  const textColor = isBull ? 'text-green-400' : 'text-red-400';
  const borderColor = isBull ? 'border-green-500' : 'border-red-500';

  return (
    <div className={`rounded-lg border-2 ${borderColor} bg-gray-900 overflow-hidden shadow-xl`}>
      <div className={`${headerBg} px-6 py-4 flex items-center justify-between`}>
        <div className="flex items-center gap-3">
          <span className="text-3xl">{isBull ? '🐂' : '🐻'}</span>
          <div>
            <h3 className="text-lg font-bold text-white">{isBull ? 'Bull Agent' : 'Bear Agent'}</h3>
            <p className="text-sm text-gray-100 opacity-90">Round {state.currentRound}</p>
          </div>
        </div>
        <div className="text-right">
          <div className="text-sm text-gray-100">Confidence</div>
          <div className="text-2xl font-bold text-white">78%</div>
        </div>
      </div>

      <div className="p-6 space-y-4">
        <div className={`rounded-lg p-4 bg-gray-800 border border-gray-700 min-h-[120px]`}>
          <p className="text-white leading-relaxed text-base">{displayText}</p>
          {isAnimating && <span className="inline-block w-2 h-6 ml-1 bg-gray-400 animate-pulse" />}
        </div>

        <div className="flex flex-wrap gap-2">
          {['high conviction', 'bullish momentum', 'technical strength'].map(tag => (
            <span
              key={tag}
              className={`inline-block px-3 py-1 rounded-full text-xs font-semibold ${
                isBull ? 'bg-green-900 text-green-300' : 'bg-red-900 text-red-300'
              }`}
            >
              {tag}
            </span>
          ))}
        </div>

        <div className="flex items-center justify-between pt-3 border-t border-gray-700">
          <span className="text-xs text-gray-500">Round {state.currentRound} argument • Just now</span>
          <span className={`px-3 py-1 rounded-md font-semibold text-sm ${textColor} bg-gray-800`}>
            Score: 65/100
          </span>
        </div>
      </div>
    </div>
  );
};

export default DebatePanel;
