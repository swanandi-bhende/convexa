'use client';

import React, { useState } from 'react';
import { useDebateStore } from '@/store/debateStore';

const StakePanel: React.FC = () => {
  const { state, dispatch } = useDebateStore();
  const [bullAmount, setBullAmount] = useState('');
  const [bearAmount, setBearAmount] = useState('');
  const [loading, setLoading] = useState(false);
  const [connectedWallet, setConnectedWallet] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'bull' | 'bear'>('bull');

  const bullTotal = parseFloat(state.bullStakeTotal) || 0;
  const bearTotal = parseFloat(state.bearStakeTotal) || 0;
  const totalPool = bullTotal + bearTotal;
  const bullPercent = totalPool > 0 ? ((bullTotal / totalPool) * 100).toFixed(1) : '50';
  const bearPercent = totalPool > 0 ? ((bearTotal / totalPool) * 100).toFixed(1) : '50';

  const handleConnect = () => {
    // Mock wallet connection
    setConnectedWallet('0x1234...5678');
  };

  const handleStake = async (side: 'bull' | 'bear') => {
    const amount = side === 'bull' ? bullAmount : bearAmount;
    if (!amount || parseFloat(amount) <= 0) return;

    setLoading(true);
    try {
      // Mock deposit
      await new Promise(resolve => setTimeout(resolve, 1000));
      dispatch({
        type: 'STAKE_UPDATED',
        payload: {
          side,
          amount: side === 'bull' ? (bullTotal + parseFloat(amount)).toFixed(4) : (bearTotal + parseFloat(amount)).toFixed(4),
        },
      });
      if (side === 'bull') setBullAmount('');
      else setBearAmount('');
      // Show success toast (simplified)
      alert(`Successfully staked ${amount} ETH on ${side.toUpperCase()}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="rounded-lg border border-gray-700 bg-gray-900 overflow-hidden shadow-xl">
      <div className="bg-gradient-to-r from-purple-600 to-blue-600 px-6 py-4">
        <h3 className="text-lg font-bold text-white">Stake Panel</h3>
        <p className="text-sm text-gray-100 mt-1">Total Pool: {totalPool.toFixed(4)} ETH</p>
      </div>

      {/* Wallet connection */}
      <div className="px-6 py-4 border-b border-gray-700">
        {connectedWallet ? (
          <div className="flex items-center justify-between">
            <div>
              <div className="text-xs text-gray-500">Connected Wallet</div>
              <div className="text-sm font-mono text-green-400">{connectedWallet}</div>
            </div>
            <button
              className="px-3 py-1 text-sm bg-red-600 hover:bg-red-700 text-white rounded transition"
              onClick={() => setConnectedWallet(null)}
            >
              Disconnect
            </button>
          </div>
        ) : (
          <button
            className="w-full px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded font-semibold transition"
            onClick={handleConnect}
          >
            Connect Wallet
          </button>
        )}
      </div>

      {/* Tabs */}
      <div className="flex border-b border-gray-700">
        <button
          onClick={() => setActiveTab('bull')}
          className={`flex-1 px-4 py-3 font-semibold transition ${activeTab === 'bull' ? 'border-b-2 border-green-500 text-green-400 bg-gray-800' : 'text-gray-400 hover:text-gray-300'}`}
        >
          📈 Bull
        </button>
        <button
          onClick={() => setActiveTab('bear')}
          className={`flex-1 px-4 py-3 font-semibold transition ${activeTab === 'bear' ? 'border-b-2 border-red-500 text-red-400 bg-gray-800' : 'text-gray-400 hover:text-gray-300'}`}
        >
          📉 Bear
        </button>
      </div>

      {/* Stake content */}
      <div className="p-6">
        {activeTab === 'bull' ? (
          <div className="space-y-4">
            <div className="flex items-end justify-between mb-4">
              <div>
                <div className="text-sm text-gray-400">Total Staked on Bull</div>
                <div className="text-3xl font-bold text-green-400">{bullTotal.toFixed(4)} ETH</div>
                <div className="text-sm text-gray-500 mt-1">{bullPercent}% of pool</div>
              </div>
              <div className="text-right">
                <div className="text-2xl font-bold text-green-500">{((bullTotal / (totalPool || 1)) * 100).toFixed(0)}%</div>
              </div>
            </div>

            {connectedWallet && (
              <div className="space-y-3">
                <div>
                  <label className="block text-sm text-gray-400 mb-2">Deposit Amount (ETH)</label>
                  <input
                    type="number"
                    step="0.01"
                    value={bullAmount}
                    onChange={e => setBullAmount(e.target.value)}
                    placeholder="0.00"
                    className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded text-white placeholder-gray-500 focus:border-green-500 focus:outline-none"
                  />
                </div>
                <button
                  onClick={() => handleStake('bull')}
                  disabled={loading || !bullAmount}
                  className="w-full px-4 py-3 bg-green-600 hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded font-semibold transition"
                >
                  {loading ? 'Confirming...' : 'Stake on Bull'}
                </button>
              </div>
            )}
          </div>
        ) : (
          <div className="space-y-4">
            <div className="flex items-end justify-between mb-4">
              <div>
                <div className="text-sm text-gray-400">Total Staked on Bear</div>
                <div className="text-3xl font-bold text-red-400">{bearTotal.toFixed(4)} ETH</div>
                <div className="text-sm text-gray-500 mt-1">{bearPercent}% of pool</div>
              </div>
              <div className="text-right">
                <div className="text-2xl font-bold text-red-500">{((bearTotal / (totalPool || 1)) * 100).toFixed(0)}%</div>
              </div>
            </div>

            {connectedWallet && (
              <div className="space-y-3">
                <div>
                  <label className="block text-sm text-gray-400 mb-2">Deposit Amount (ETH)</label>
                  <input
                    type="number"
                    step="0.01"
                    value={bearAmount}
                    onChange={e => setBearAmount(e.target.value)}
                    placeholder="0.00"
                    className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded text-white placeholder-gray-500 focus:border-red-500 focus:outline-none"
                  />
                </div>
                <button
                  onClick={() => handleStake('bear')}
                  disabled={loading || !bearAmount}
                  className="w-full px-4 py-3 bg-red-600 hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded font-semibold transition"
                >
                  {loading ? 'Confirming...' : 'Stake on Bear'}
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default StakePanel;
