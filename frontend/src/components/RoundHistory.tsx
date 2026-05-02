'use client';

import React, { useState, useRef, useEffect } from 'react';
import { useDebateStore } from '@/store/debateStore';

const RoundHistory: React.FC = () => {
  const { state } = useDebateStore();
  const { roundHistory } = state;
  const [expandedRound, setExpandedRound] = useState<number | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current && roundHistory.length > 0) {
      scrollRef.current.scrollTop = 0;
    }
  }, [roundHistory]);

  return (
    <div className="rounded-lg border border-gray-700 bg-gray-900 overflow-hidden shadow-xl flex flex-col h-[600px]">
      <div className="bg-gradient-to-r from-blue-600 to-cyan-600 px-6 py-4 sticky top-0 z-10">
        <h3 className="text-lg font-bold text-white">Round History</h3>
        <p className="text-sm text-gray-100 mt-1">{roundHistory.length} rounds completed</p>
      </div>

      <div ref={scrollRef} className="flex-1 overflow-y-auto space-y-2 p-4">
        {roundHistory.length === 0 ? (
          <div className="flex items-center justify-center h-full">
            <p className="text-gray-500 text-center">No rounds yet. Debate is starting...</p>
          </div>
        ) : (
          roundHistory.map(round => {
            const isCurrent = round.roundNumber === state.currentRound;
            const isExpanded = expandedRound === round.roundNumber;

            return (
              <div
                key={round.roundNumber}
                className={`rounded-lg p-4 border-l-4 transition-all ${
                  round.winner === 'bull'
                    ? 'border-l-green-500 bg-gray-800 hover:bg-gray-750'
                    : round.winner === 'bear'
                      ? 'border-l-red-500 bg-gray-800 hover:bg-gray-750'
                      : 'border-l-yellow-500 bg-gray-800 hover:bg-gray-750'
                } ${isCurrent ? 'ring-2 ring-purple-500 shadow-lg' : ''}`}
              >
                <div className="flex items-center justify-between cursor-pointer" onClick={() => setExpandedRound(isExpanded ? null : round.roundNumber)}>
                  <div className="flex items-center gap-3 flex-1">
                    <span className="font-bold text-white">Round {round.roundNumber}</span>
                    <span
                      className={`px-3 py-1 rounded-full text-xs font-bold ${
                        round.winner === 'bull'
                          ? 'bg-green-900 text-green-300'
                          : round.winner === 'bear'
                            ? 'bg-red-900 text-red-300'
                            : 'bg-yellow-900 text-yellow-300'
                      }`}
                    >
                      {round.winner === 'bull' ? '🐂 BULL WON' : round.winner === 'bear' ? '🐻 BEAR WON' : '⚖️ TIE'}
                    </span>
                    {isCurrent && <span className="text-purple-400 text-xs font-semibold">CURRENT</span>}
                  </div>
                  <button className="text-gray-400 hover:text-gray-300 transition">
                    {isExpanded ? '▼' : '▶'}
                  </button>
                </div>

                {/* Mini meter */}
                <div className="mt-3 flex items-center gap-2">
                  <div className="flex-1 h-6 bg-gray-700 rounded-full overflow-hidden flex">
                    <div
                      className="bg-green-500 flex items-center justify-center text-xs font-bold text-white"
                      style={{ width: `${(round.bullScore / (round.bullScore + round.bearScore || 1)) * 100}%` }}
                    >
                      {round.bullScore}
                    </div>
                    <div
                      className="bg-red-500 flex items-center justify-center text-xs font-bold text-white"
                      style={{ width: `${(round.bearScore / (round.bullScore + round.bearScore || 1)) * 100}%` }}
                    >
                      {round.bearScore}
                    </div>
                  </div>
                </div>

                {/* Expanded content */}
                {isExpanded && (
                  <div className="mt-4 pt-4 border-t border-gray-700 space-y-2 animate-in fade-in slide-in-from-top-2 duration-200">
                    <div>
                      <div className="text-xs text-gray-500 mb-1">Judge Reasoning</div>
                      <p className="text-sm text-gray-300 leading-relaxed">{round.judgeReasoning || 'No reasoning provided'}</p>
                    </div>
                    <div className="grid grid-cols-2 gap-3 pt-2">
                      <div className="bg-gray-700 rounded p-2">
                        <div className="text-xs text-green-400">Bull Score</div>
                        <div className="text-lg font-bold text-green-300">{round.bullScore}</div>
                      </div>
                      <div className="bg-gray-700 rounded p-2">
                        <div className="text-xs text-red-400">Bear Score</div>
                        <div className="text-lg font-bold text-red-300">{round.bearScore}</div>
                      </div>
                    </div>
                    <div className="text-xs text-gray-500 pt-2">{new Date(round.timestamp).toLocaleTimeString()}</div>
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};

export default RoundHistory;
