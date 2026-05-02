'use client';

import React, { useEffect, useState } from 'react';
import { useDebateStore } from '@/store/debateStore';

const ConvictionMeter: React.FC = () => {
  const { state } = useDebateStore();
  const { currentBullScore, currentBearScore, connectionStatus, currentRound } = state;
  const [flashKey, setFlashKey] = useState(0);
  const [prevBullScore, setPrevBullScore] = useState(currentBullScore);
  const [prevBearScore, setPrevBearScore] = useState(currentBearScore);

  // Trigger flash animation when scores change
  useEffect(() => {
    if (currentBullScore !== prevBullScore || currentBearScore !== prevBearScore) {
      setFlashKey(k => k + 1);
      setPrevBullScore(currentBullScore);
      setPrevBearScore(currentBearScore);
    }
  }, [currentBullScore, currentBearScore, prevBullScore, prevBearScore]);

  const total = currentBullScore + currentBearScore || 1;
  const bullPercent = (currentBullScore / total) * 100;
  const bearPercent = (currentBearScore / total) * 100;
  const leadingScore = Math.max(currentBullScore, currentBearScore);
  const distanceToWin = Math.max(0, 70 - leadingScore);

  const isConnected = connectionStatus === 'live';
  const isReconnecting = connectionStatus === 'reconnecting';

  return (
    <div className="w-full bg-gradient-to-b from-gray-900 to-gray-800 p-8 rounded-lg border border-gray-700 shadow-2xl">
      <style>{`
        @keyframes pulse-bright {
          0%, 100% { filter: brightness(1); }
          50% { filter: brightness(1.2); }
        }
        @keyframes flash-white {
          0% { filter: brightness(2); }
          100% { filter: brightness(1); }
        }
        .pulse-leading {
          animation: pulse-bright 2s ease-in-out infinite;
        }
        .flash-update {
          animation: flash-white 0.5s ease-out;
        }
      `}</style>

      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold text-white">Conviction Meter</h2>
          <p className="text-sm text-gray-400">Round {currentRound}</p>
        </div>
        <div className="flex items-center gap-3">
          {isConnected && (
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 bg-green-400 rounded-full animate-pulse" />
              <span className="text-green-400 text-sm font-semibold">LIVE</span>
            </div>
          )}
          {isReconnecting && (
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 bg-yellow-400 rounded-full animate-spin" />
              <span className="text-yellow-400 text-sm font-semibold">RECONNECTING</span>
            </div>
          )}
          {!isConnected && !isReconnecting && (
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 bg-red-400 rounded-full" />
              <span className="text-red-400 text-sm font-semibold">DISCONNECTED</span>
            </div>
          )}
        </div>
      </div>

      <div className="mb-8">
        <div className="flex items-end justify-between mb-4">
          <div className="text-center flex-1">
            <div className={`text-5xl font-bold mb-2 ${bullPercent > 50 ? 'text-green-400 pulse-leading' : 'text-green-500'}`}>
              {currentBullScore}
            </div>
            <div className="text-lg font-semibold text-green-400">BULL</div>
          </div>
          <div className="flex-1 flex justify-center">
            <div className="text-gray-500 text-lg">/</div>
          </div>
          <div className="text-center flex-1">
            <div className={`text-5xl font-bold mb-2 ${bearPercent > 50 ? 'text-red-400 pulse-leading' : 'text-red-500'}`}>
              {currentBearScore}
            </div>
            <div className="text-lg font-semibold text-red-400">BEAR</div>
          </div>
        </div>

        {/* Main conviction bar */}
        <div
          key={flashKey}
          className={`w-full h-16 bg-gray-700 rounded-lg overflow-hidden border border-gray-600 flex ${flashKey > 0 ? 'flash-update' : ''}`}
        >
          <div
            className="bg-gradient-to-r from-green-500 to-green-400 flex items-center justify-center text-white font-bold text-sm transition-all duration-800 ease-in-out"
            style={{ width: `${bullPercent}%` }}
          >
            {bullPercent > 20 && `${bullPercent.toFixed(0)}%`}
          </div>
          <div
            className="bg-gradient-to-r from-red-500 to-red-400 flex items-center justify-end pr-4 text-white font-bold text-sm transition-all duration-800 ease-in-out"
            style={{ width: `${bearPercent}%` }}
          >
            {bearPercent > 20 && `${bearPercent.toFixed(0)}%`}
          </div>
        </div>
      </div>

      {/* Distance to win progress */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs text-gray-400">Distance to 70-point win</span>
          <span className="text-sm font-semibold text-white">{distanceToWin} points</span>
        </div>
        <div className="w-full h-2 bg-gray-700 rounded-full overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-yellow-400 to-yellow-500 transition-all duration-800"
            style={{ width: `${Math.min(100, (leadingScore / 70) * 100)}%` }}
          />
        </div>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-3 gap-4 text-center text-xs text-gray-400">
        <div>
          <div className="text-gray-500 mb-1">Bull Momentum</div>
          <div className="text-green-400 font-semibold text-lg">+{Math.abs(currentBullScore - currentBearScore)}</div>
        </div>
        <div>
          <div className="text-gray-500 mb-1">Total Score</div>
          <div className="text-white font-semibold text-lg">{total}</div>
        </div>
        <div>
          <div className="text-gray-500 mb-1">Leading Side</div>
          <div className={`font-semibold text-lg ${currentBullScore > currentBearScore ? 'text-green-400' : currentBearScore > currentBullScore ? 'text-red-400' : 'text-gray-400'}`}>
            {currentBullScore > currentBearScore ? 'BULL' : currentBearScore > currentBullScore ? 'BEAR' : 'TIE'}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ConvictionMeter;
