'use client';

import React, { useState } from 'react';
import { useDebateStore } from '@/store/debateStore';

const TransactionLog: React.FC = () => {
  const { state } = useDebateStore();
  const { transactions } = state;
  const [showAll, setShowAll] = useState(false);

  const displayTxs = showAll ? transactions : transactions.slice(0, 10);
  const totalGasGwei = transactions.length * 0.5; // Mock gas calculation
  const successRate = transactions.length > 0 ? ((transactions.filter(t => t.status === 'confirmed').length / transactions.length) * 100).toFixed(1) : '0';

  const typeIcon = (type: string) => {
    switch (type) {
      case 'conviction':
        return '⚖️';
      case 'deposit':
        return '📥';
      case 'settlement':
        return '💰';
      case 'swap':
        return '🔄';
      default:
        return '📋';
    }
  };

  const typeLabel = (type: string) => {
    switch (type) {
      case 'conviction':
        return 'Conviction Update';
      case 'deposit':
        return 'Deposit';
      case 'settlement':
        return 'Settlement';
      case 'swap':
        return 'Uniswap Swap';
      default:
        return 'Unknown';
    }
  };

  const timeAgo = (timestamp: number) => {
    const seconds = Math.floor((Date.now() - timestamp) / 1000);
    if (seconds < 60) return `${seconds}s ago`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
    return `${Math.floor(seconds / 3600)}h ago`;
  };

  return (
    <div className="rounded-lg border border-gray-700 bg-gray-900 overflow-hidden shadow-xl flex flex-col h-[600px]">
      <div className="bg-gradient-to-r from-pink-600 to-orange-600 px-6 py-4 sticky top-0 z-10">
        <h3 className="text-lg font-bold text-white">Transaction Log</h3>
        <p className="text-sm text-gray-100 mt-1">{transactions.length} transactions</p>
      </div>

      {/* Stats bar */}
      {transactions.length > 0 && (
        <div className="px-6 py-3 bg-gray-800 border-b border-gray-700 grid grid-cols-3 gap-4 text-xs">
          <div>
            <div className="text-gray-500">Total Transactions</div>
            <div className="text-lg font-bold text-white">{transactions.length}</div>
          </div>
          <div>
            <div className="text-gray-500">Gas Used</div>
            <div className="text-lg font-bold text-white">{totalGasGwei.toFixed(2)} Gwei</div>
          </div>
          <div>
            <div className="text-gray-500">Success Rate</div>
            <div className="text-lg font-bold text-green-400">{successRate}%</div>
          </div>
        </div>
      )}

      {/* Transaction list */}
      <div className="flex-1 overflow-y-auto space-y-1 p-4">
        {transactions.length === 0 ? (
          <div className="flex items-center justify-center h-full">
            <p className="text-gray-500 text-center">Waiting for transactions...</p>
          </div>
        ) : (
          displayTxs.map((tx, idx) => (
            <div
              key={idx}
              className={`rounded-lg p-3 flex items-center justify-between border transition-all ${
                tx.status === 'confirmed'
                  ? 'border-green-800 bg-green-900 bg-opacity-20'
                  : tx.status === 'pending'
                    ? 'border-yellow-800 bg-yellow-900 bg-opacity-20'
                    : 'border-red-800 bg-red-900 bg-opacity-20'
              } hover:border-gray-600`}
            >
              <div className="flex items-center gap-3 flex-1 min-w-0">
                <span className="text-lg flex-shrink-0">{typeIcon(tx.type)}</span>
                <div className="min-w-0 flex-1">
                  <div className="font-semibold text-sm text-white">{typeLabel(tx.type)}</div>
                  <div className="text-xs font-mono text-gray-400 truncate">{tx.hash}</div>
                </div>
              </div>

              <div className="flex items-center gap-2 flex-shrink-0 ml-4">
                {/* Status dot */}
                <div
                  className={`w-2 h-2 rounded-full ${
                    tx.status === 'confirmed'
                      ? 'bg-green-400'
                      : tx.status === 'pending'
                        ? 'bg-yellow-400 animate-pulse'
                        : 'bg-red-400'
                  }`}
                />

                {/* Amount and time */}
                <div className="text-right text-xs">
                  <div className="font-semibold text-white">${parseFloat(tx.amount).toFixed(2)}</div>
                  <div className="text-gray-500">{timeAgo(tx.timestamp)}</div>
                </div>

                {/* Explorer link */}
                <a
                  href={`https://sepolia.unichain.explorer/tx/${tx.hash}`}
                  target="_blank"
                  rel="noreferrer"
                  className="text-blue-400 hover:text-blue-300 text-xs font-semibold ml-2 flex-shrink-0"
                >
                  →
                </a>
              </div>
            </div>
          ))
        )}
      </div>

      {!showAll && transactions.length > 10 && (
        <div className="px-6 py-3 border-t border-gray-700 bg-gray-800">
          <button
            onClick={() => setShowAll(true)}
            className="w-full py-2 text-blue-400 hover:text-blue-300 font-semibold text-sm transition"
          >
            View all {transactions.length} transactions →
          </button>
        </div>
      )}
    </div>
  );
};

export default TransactionLog;
