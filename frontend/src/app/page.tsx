'use client';

import React, { useEffect } from 'react';
import { DebateProvider, useDebateStore } from '@/store/debateStore';
import ConvictionMeter from '@/components/ConvictionMeter';
import DebatePanel from '@/components/DebatePanel';
import StakePanel from '@/components/StakePanel';
import RoundHistory from '@/components/RoundHistory';
import TransactionLog from '@/components/TransactionLog';
import { useContractEvents } from '@/lib/websocket';

function DashboardContent() {
  const { dispatch, state } = useDebateStore();

  // Initialize with mock data on mount
  useEffect(() => {
    const initializeDebate = async () => {
      try {
        // Fetch initial debate state
        const stateRes = await fetch('/api/debate-state');
        const debateState = await stateRes.json();

        // Fetch round history
        const historyRes = await fetch('/api/round-history');
        const roundHistory = await historyRes.json();

        // Fetch transactions
        const txRes = await fetch('/api/transactions');
        const transactions = await txRes.json();

        // Dispatch to store
        roundHistory.forEach((round: any) => {
          dispatch({
            type: 'CONVICTION_UPDATED',
            payload: {
              roundNumber: round.roundNumber,
              bullScore: round.bullScore,
              bearScore: round.bearScore,
              timestamp: round.timestamp,
            },
          });
        });

        transactions.forEach((tx: any) => {
          dispatch({
            type: 'TRANSACTION_ADDED',
            payload: {
              hash: tx.hash,
              type: tx.type,
              from: tx.from,
              amount: tx.amount,
              timestamp: tx.timestamp,
              status: tx.status,
              keeperJobId: tx.keeperJobId,
            },
          });
        });

        dispatch({
          type: 'STAKE_UPDATED',
          payload: {
            side: 'bull',
            amount: debateState.bullStakeTotal,
          },
        });

        dispatch({
          type: 'STAKE_UPDATED',
          payload: {
            side: 'bear',
            amount: debateState.bearStakeTotal,
          },
        });

        // Set mock arguments
        dispatch({
          type: 'ARGUMENT_RECEIVED',
          payload: {
            side: 'bull',
            text: 'ETH price will continue its bullish trajectory based on strong on-chain metrics and upcoming protocol upgrades. The fear around macro headwinds is overblown.',
            round: debateState.currentRound,
          },
        });

        dispatch({
          type: 'ARGUMENT_RECEIVED',
          payload: {
            side: 'bear',
            text: 'The broader macro environment remains fragile. Despite recent rallies, ETH faces significant resistance at $2,800 and could easily pull back 15-20% if risk sentiment shifts.',
            round: debateState.currentRound,
          },
        });
      } catch (e) {
        console.error('Failed to initialize debate', e);
      }
    };

    initializeDebate();
  }, [dispatch]);

  // Setup websocket event listeners
  useContractEvents(
    (convictionEvent) => {
      dispatch({
        type: 'CONVICTION_UPDATED',
        payload: convictionEvent,
      });
    },
    (depositEvent) => {
      dispatch({
        type: 'DEPOSIT_MADE',
        payload: depositEvent,
      });
    },
    (status) => {
      dispatch({
        type: 'CONNECTION_STATUS_CHANGED',
        payload: status,
      });
    }
  );

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-950 via-gray-900 to-gray-950">
      {/* Top navigation */}
      <nav className="bg-gray-900 border-b border-gray-700 sticky top-0 z-50 backdrop-blur-sm">
        <div className="max-w-full px-6 py-4 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-white">Convexa Live</h1>
            <p className="text-xs text-gray-400 mt-1">
              Debate ID: 0x{Math.random().toString(16).slice(2, 10)} • Unichain Sepolia
            </p>
          </div>
          <div className="flex items-center gap-4">
            <div className="text-right">
              <div className="text-xs text-gray-500">Session Round</div>
              <div className="text-lg font-bold text-white">{state.currentRound}</div>
            </div>
            <div
              className={`w-3 h-3 rounded-full ${
                state.connectionStatus === 'live'
                  ? 'bg-green-400 animate-pulse'
                  : state.connectionStatus === 'reconnecting'
                    ? 'bg-yellow-400'
                    : 'bg-red-400'
              }`}
            />
          </div>
        </div>
      </nav>

      {/* Main content */}
      <main className="max-w-full px-4 py-8 space-y-8">
        {/* Conviction meter - full width */}
        <ConvictionMeter />

        {/* Debate panels - two columns */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <DebatePanel side="bull" />
          <DebatePanel side="bear" />
        </div>

        {/* Bottom three-column grid: Stake, History, Log */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <StakePanel />
          <RoundHistory />
          <TransactionLog />
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-gray-700 px-6 py-4 mt-12 text-center text-xs text-gray-500">
        <p>Conviction-weighted debate market powered by Unichain & KeeperHub</p>
      </footer>
    </div>
  );
}

export default function Home() {
  return (
    <DebateProvider>
      <DashboardContent />
    </DebateProvider>
  );
}
