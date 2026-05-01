'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import {
  BullCard,
  BearCard,
  JudgeVerdict,
  RoundTimer,
  MarketSnapshot,
  ConvictionVotingModal,
} from '@/components';
import { useRealTimeDebate } from '@/hooks/useDebate';
import { useConvictionVote } from '@/hooks/useConviction';
import { WebSocketMessage, DebateSessionResponse } from '@/types/api';

// Mock debate data - fallback when API data unavailable
const getMockDebate = (id: string): DebateSessionResponse => {
  const mockRound: DebateSessionResponse['rounds'][0] = {
    roundNumber: 7,
    status: 'in-progress',
    timeRemaining: 145,
    bullRound: {
      id: 1,
      roundNumber: 7,
      tokenPair: 'ETH/USDC',
      argument:
        'Ethereum is showing strong bullish signals. Recent upgrades to the consensus layer have reduced energy consumption by 99.9%, addressing major environmental concerns. Enterprise adoption continues to accelerate with major financial institutions integrating ETH for settlement. Current technical analysis shows a golden cross forming on the daily chart, historically a bullish indicator. The upcoming Shanghai upgrade will introduce staking rewards, creating economic incentives for network participation and reducing circulating supply.',
      confidence: 72,
      keyMetrics: ['Technical: 8.2/10', 'Sentiment: Very Bullish'],
      rawMarketData: {},
      axlDeliveryStatus: 'delivered',
      timestamp: new Date().toISOString(),
    },
    bearRound: {
      id: 2,
      roundNumber: 7,
      tokenPair: 'ETH/USDC',
      argument:
        'Despite recent optimism, Ethereum faces significant headwinds. Macroeconomic uncertainty and rising interest rates are putting pressure on all risk assets. The regulatory environment remains unclear, with multiple jurisdictions considering stricter rules on crypto. Recent data shows declining transaction volume and increasing user acquisition costs. Competition from layer-2 solutions is fragmenting liquidity and value. The token is trading well above historical valuations, creating limited upside potential while downside risks remain substantial.',
      confidence: 58,
      keyMetrics: ['Risk: 7.1/10', 'Valuation: Overextended'],
      rawMarketData: {},
      axlDeliveryStatus: 'delivered',
      timestamp: new Date().toISOString(),
    },
    judgeVerdict: undefined,
    marketData: {
      tokenPair: 'ETH/USDC',
      currentPrice: 3248.52,
      priceChange24h: 8.5,
      volume24h: 18500000000,
      volatility: 2.4,
      timestamp: new Date().toISOString(),
      sparkline: [3150, 3180, 3220, 3190, 3210, 3240, 3220, 3248],
    },
    bullCumulativeScore: 510,
    bearCumulativeScore: 406,
  };

  return {
    id: parseInt(id),
    sessionId: `session-${id}`,
    tokenPair: 'ETH/USDC',
    startTime: new Date(Date.now() - 30 * 60 * 1000).toISOString(),
    totalRounds: 10,
    currentRound: 7,
    status: 'RUNNING',
    currentBullConviction: 72,
    currentBearConviction: 58,
    settlementTriggered: false,
    rounds: [mockRound],
  };
};

export default function DebateDetailPage({
  params,
}: {
  params: { debateId: string };
}) {
  const { debateId } = params;
  const { data, loading, error, connected, connectionError, refetch } =
    useRealTimeDebate(debateId);
  const [showConnectionStatus, setShowConnectionStatus] = useState(true);
  const [votingModal, setVotingModal] = useState<'bull' | 'bear' | null>(null);
  const { submitVote, isLoading: isVoting } = useConvictionVote(debateId, 'user-123');

  // Fallback to mock data if API data unavailable
  const mockData = getMockDebate(debateId);
  const displayData = data || mockData;

  // Get current round data
  const currentRound = displayData.rounds?.[displayData.currentRound - 1] || displayData.rounds?.[0];
  const bullRound = currentRound?.bullRound;
  const bearRound = currentRound?.bearRound;
  const verdict = currentRound?.judgeVerdict;
  const marketData = currentRound?.marketData;

  return (
    <main className="space-y-lg">
      {/* Connection Status Banner */}
      {showConnectionStatus && (
        <div
          className={`rounded-lg border p-md flex items-center justify-between ${
            connected
              ? 'bg-success-50 border-success-500 text-success-700'
              : connectionError
                ? 'bg-warning-50 border-warning-500 text-warning-700'
                : 'bg-bull-50 border-bull-500 text-bull-700'
          }`}
        >
          <div className="flex items-center gap-md">
            <div
              className={`w-2 h-2 rounded-full ${
                connected ? 'bg-success-500' : 'bg-warning-500'
              } animate-pulse`}
            />
            <span className="text-sm font-medium">
              {connected
                ? '✓ Live updates connected'
                : connectionError || '⟳ Connecting...'}
            </span>
          </div>
          <button
            onClick={() => setShowConnectionStatus(false)}
            className="text-sm opacity-70 hover:opacity-100"
          >
            ✕
          </button>
        </div>
      )}

      {/* Loading State */}
      {loading && !data && (
        <div className="rounded-lg border border-border-light bg-surface p-lg text-center">
          <div className="space-y-md">
            <div className="flex justify-center gap-2">
              <div className="w-2 h-2 rounded-full bg-bull-500 animate-bounce" />
              <div className="w-2 h-2 rounded-full bg-bull-500 animate-bounce"
                style={{ animationDelay: '0.2s' }} />
              <div className="w-2 h-2 rounded-full bg-bull-500 animate-bounce"
                style={{ animationDelay: '0.4s' }} />
            </div>
            <p className="text-text-secondary">Loading debate data...</p>
          </div>
        </div>
      )}

      {/* Error State */}
      {error && !data && (
        <div className="rounded-lg border border-warning-500 bg-warning-50 p-lg">
          <div className="flex items-start justify-between">
            <div>
              <h3 className="font-semibold text-warning-700 mb-sm">Error</h3>
              <p className="text-warning-600 text-sm mb-md">{error.error}</p>
              {error.details && (
                <p className="text-warning-600 text-xs opacity-75">
                  {JSON.stringify(error.details)}
                </p>
              )}
            </div>
            <button
              onClick={refetch}
              className="px-md py-sm bg-warning-500 text-white rounded-md text-sm hover:bg-warning-600 transition-colors"
            >
              Retry
            </button>
          </div>
        </div>
      )}

      {/* Header with Back Button */}
      {(data || !loading) && (
        <>
          <div className="flex items-center justify-between mb-lg">
            <div>
              <Link
                href="/debates/active"
                className="text-bull-600 hover:text-bull-700 transition-colors mb-md inline-block text-body-md"
              >
                ← Back to Active Debates
              </Link>
              <h1 className="text-heading-lg font-bold text-text-primary">
                Live Debate: {displayData.tokenPair}
              </h1>
              <p className="text-text-secondary text-body-md mt-sm">
                Round {displayData.currentRound} of {displayData.totalRounds} •{' '}
                {displayData.status}
              </p>
            </div>
          </div>

          {/* Main Debate Layout - 3 Column Desktop, Stack Mobile */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-lg">
            {/* Left: Bull Card */}
            <div>
              {bullRound ? (
                <BullCard
                  agentName={bullRound.argument.substring(0, 20)}
                  argument={bullRound.argument}
                  confidence={bullRound.confidence}
                  metrics={
                    typeof bullRound.keyMetrics === 'string'
                      ? JSON.parse(bullRound.keyMetrics).map((m: string) => ({
                          label: m.split(':')[0],
                          value: m.split(':')[1],
                        }))
                      : []
                  }
                  isActive={displayData.currentRound === currentRound?.roundNumber}
                />
              ) : (
                <div className="rounded-lg border border-border-light bg-surface p-lg text-center text-text-secondary">
                  Waiting for Bull argument...
                </div>
              )}
            </div>

            {/* Center: Market Data & Round Info */}
            <div className="space-y-lg">
              {/* Market Snapshot */}
              {marketData ? (
                <MarketSnapshot
                  tokenPair={marketData.tokenPair}
                  currentPrice={marketData.currentPrice}
                  priceChange24h={marketData.priceChange24h}
                  volume24h={marketData.volume24h}
                  volatility={marketData.volatility}
                  timestamp={marketData.timestamp}
                  sparkline={marketData.sparkline}
                />
              ) : (
                <div className="rounded-lg border border-border-light bg-surface p-lg text-center text-text-secondary">
                  No market data
                </div>
              )}

              {/* Round Timer */}
              <RoundTimer
                currentRound={displayData.currentRound}
                totalRounds={displayData.totalRounds}
                timeRemaining={currentRound?.timeRemaining}
                status={currentRound?.status || displayData.status}
              />

              {/* Conviction Tracker - Live Data */}
              <div className="rounded-lg border border-border-light bg-white p-lg">
                <h3 className="font-semibold mb-lg text-heading-md text-text-primary">
                  Current Conviction
                </h3>

                {/* Bull Conviction */}
                <div className="mb-lg">
                  <div className="flex justify-between mb-sm">
                    <span className="font-semibold text-label-md text-bull-600">
                      Bull Conviction
                    </span>
                    <span className="font-bold text-body-md text-bull-500">
                      {displayData.currentBullConviction}
                    </span>
                  </div>
                  <div className="h-3 rounded-full bg-bull-100 overflow-hidden">
                    <div
                      className="h-full transition-all duration-500 bg-bull-500"
                      style={{
                        width: `${Math.min(
                          100,
                          (displayData.currentBullConviction /
                            (displayData.currentBullConviction +
                              displayData.currentBearConviction)) *
                            100
                        )}%`,
                      }}
                    />
                  </div>
                </div>

                {/* Bear Conviction */}
                <div>
                  <div className="flex justify-between mb-sm">
                    <span className="font-semibold text-label-md text-bear-600">
                      Bear Conviction
                    </span>
                    <span className="font-bold text-body-md text-bear-500">
                      {displayData.currentBearConviction}
                    </span>
                  </div>
                  <div className="h-3 rounded-full bg-bear-100 overflow-hidden">
                    <div
                      className="h-full transition-all duration-500 bg-bear-500"
                      style={{
                        width: `${Math.min(
                          100,
                          (displayData.currentBearConviction /
                            (displayData.currentBullConviction +
                              displayData.currentBearConviction)) *
                            100
                        )}%`,
                      }}
                    />
                  </div>
                </div>

                {/* Total Votes */}
                <div className="mt-lg pt-lg border-t border-border-light text-center text-text-secondary mb-lg">
                  Combined:{' '}
                  {displayData.currentBullConviction +
                    displayData.currentBearConviction}{' '}
                  votes
                </div>

                {/* Voting Buttons */}
                <div className="grid grid-cols-2 gap-md">
                  <button
                    onClick={() => setVotingModal('bull')}
                    disabled={isVoting || displayData.status !== 'RUNNING'}
                    className="px-md py-sm bg-bull-50 hover:bg-bull-100 text-bull-600 font-semibold rounded-md transition-colors disabled:opacity-50"
                  >
                    Vote Bull 📈
                  </button>
                  <button
                    onClick={() => setVotingModal('bear')}
                    disabled={isVoting || displayData.status !== 'RUNNING'}
                    className="px-md py-sm bg-bear-50 hover:bg-bear-100 text-bear-600 font-semibold rounded-md transition-colors disabled:opacity-50"
                  >
                    Vote Bear 📉
                  </button>
                </div>
              </div>
            </div>

            {/* Right: Bear Card */}
            <div>
              {bearRound ? (
                <BearCard
                  agentName={bearRound.argument.substring(0, 20)}
                  argument={bearRound.argument}
                  confidence={bearRound.confidence}
                  metrics={
                    typeof bearRound.keyMetrics === 'string'
                      ? JSON.parse(bearRound.keyMetrics).map((m: string) => ({
                          label: m.split(':')[0],
                          value: m.split(':')[1],
                        }))
                      : []
                  }
                  isActive={displayData.currentRound === currentRound?.roundNumber}
                />
              ) : (
                <div className="rounded-lg border border-border-light bg-surface p-lg text-center text-text-secondary">
                  Waiting for Bear argument...
                </div>
              )}
            </div>
          </div>

          {/* Judge Verdict - Full Width Bottom */}
          <div className="lg:col-span-3">
            {verdict ? (
              <JudgeVerdict
                status="revealed"
                tokenPair={displayData.tokenPair}
                winner={verdict.winner as 'bull' | 'bear'}
                scoreBreakdown={{
                  bullScore: verdict.bullScore,
                  bearScore: verdict.bearScore,
                  reasoning: verdict.reasoning,
                }}
              />
            ) : (
              <JudgeVerdict
                status="pending"
                tokenPair={displayData.tokenPair}
              />
            )}
          </div>

          {/* Additional Info Section */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-lg rounded-lg border border-border-light bg-surface p-lg">
            <div>
              <h4 className="font-semibold mb-md text-heading-md text-text-primary">
                About This Debate
              </h4>
              <p className="text-text-secondary text-body-md leading-relaxed">
                This debate is comparing Bull and Bear perspectives on{' '}
                {displayData.tokenPair} price movements. Both agents present
                evidence-based arguments supported by technical analysis, market
                data, and sentiment indicators.
              </p>
            </div>
            <div>
              <h4 className="font-semibold mb-md text-heading-md text-text-primary">
                How It Works
              </h4>
              <ul className="text-text-secondary text-body-md space-y-sm">
                <li>1. Agents present arguments each round</li>
                <li>2. Judge evaluates argument quality</li>
                <li>3. Scores determine round winner</li>
                <li>4. Best overall argument wins debate</li>
              </ul>
            </div>
          </div>
        </>
      )}

      {/* Voting Modal */}
      {votingModal && (
        <ConvictionVotingModal
          debateId={debateId}
          isOpen={!!votingModal}
          side={votingModal}
          onClose={() => setVotingModal(null)}
          onVote={async (amount: number) => {
            await submitVote(votingModal, amount);
            setVotingModal(null);
          }}
          isLoading={isVoting}
        />
      )}
    </main>
  );
}
