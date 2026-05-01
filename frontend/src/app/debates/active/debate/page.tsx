import React from 'react';
import Link from 'next/link';
import {
  BullCard,
  BearCard,
  JudgeVerdict,
  RoundTimer,
  MarketSnapshot,
} from '@/components';

// Mock debate data - will be replaced with real API data in Step 5
const mockDebate = {
  id: 1,
  tokenPair: 'ETH/USDC',
  currentRound: 7,
  totalRounds: 10,
  status: 'in-progress' as const,
  timeRemaining: 145, // seconds
  bullAgent: {
    name: 'Bull Agent Alpha',
    argument:
      'Ethereum is showing strong bullish signals. Recent upgrades to the consensus layer have reduced energy consumption by 99.9%, addressing major environmental concerns. Enterprise adoption continues to accelerate with major financial institutions integrating ETH for settlement. Current technical analysis shows a golden cross forming on the daily chart, historically a bullish indicator. The upcoming Shanghai upgrade will introduce staking rewards, creating economic incentives for network participation and reducing circulating supply.',
    confidence: 72,
    metrics: [
      { label: 'Technical Score', value: '8.2/10' },
      { label: 'Sentiment', value: 'Very Bullish' },
    ],
  },
  bearAgent: {
    name: 'Bear Agent Omega',
    argument:
      'Despite recent optimism, Ethereum faces significant headwinds. Macroeconomic uncertainty and rising interest rates are putting pressure on all risk assets. The regulatory environment remains unclear, with multiple jurisdictions considering stricter rules on crypto. Recent data shows declining transaction volume and increasing user acquisition costs. Competition from layer-2 solutions is fragmenting liquidity and value. The token is trading well above historical valuations, creating limited upside potential while downside risks remain substantial.',
    confidence: 58,
    metrics: [
      { label: 'Risk Score', value: '7.1/10' },
      { label: 'Valuation', value: 'Overextended' },
    ],
  },
  marketData: {
    eth: {
      tokenPair: 'ETH/USDC',
      currentPrice: 3248.52,
      priceChange24h: 8.5,
      volume24h: 18500000000,
      volatility: 2.4,
      timestamp: new Date().toISOString(),
      sparkline: [3150, 3180, 3220, 3190, 3210, 3240, 3220, 3248],
    },
  },
  verdict: {
    status: 'pending' as 'pending' | 'revealed',
    tokenPair: 'ETH/USDC',
  },
  bullConviction: 72,
  bearConviction: 58,
};

export default function DebateDetailPage({
  params,
}: {
  params: { debateId: string };
}) {
  const debate = mockDebate;

  return (
    <main className="space-y-lg">
      {/* Header with Back Button */}
      <div className="flex items-center justify-between mb-lg">
        <div>
          <Link
            href="/debates/active"
            className="text-bull-600 hover:text-bull-700 transition-colors mb-md inline-block text-body-md"
          >
            ← Back to Active Debates
          </Link>
          <h1 className="text-heading-lg font-bold text-text-primary">
            Live Debate: {debate.tokenPair}
          </h1>
          <p className="text-text-secondary text-body-md mt-sm">
            Round {debate.currentRound} of {debate.totalRounds} • In Progress
          </p>
        </div>
      </div>

      {/* Main Debate Layout - 3 Column Desktop, Stack Mobile */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-lg">
        {/* Left: Bull Card */}
        <div>
          <BullCard
            agentName={debate.bullAgent.name}
            argument={debate.bullAgent.argument}
            confidence={debate.bullAgent.confidence}
            metrics={debate.bullAgent.metrics}
            isActive={true}
          />
        </div>

        {/* Center: Market Data & Round Info */}
        <div className="space-y-lg">
          {/* Market Snapshot */}
          <MarketSnapshot
            tokenPair={debate.marketData.eth.tokenPair}
            currentPrice={debate.marketData.eth.currentPrice}
            priceChange24h={debate.marketData.eth.priceChange24h}
            volume24h={debate.marketData.eth.volume24h}
            volatility={debate.marketData.eth.volatility}
            timestamp={debate.marketData.eth.timestamp}
            sparkline={debate.marketData.eth.sparkline}
          />

          {/* Round Timer */}
          <RoundTimer
            currentRound={debate.currentRound}
            totalRounds={debate.totalRounds}
            timeRemaining={debate.timeRemaining}
            status={debate.status}
          />

          {/* Conviction Tracker - Simple Version */}
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
                  {debate.bullConviction}%
                </span>
              </div>
              <div className="h-3 rounded-full bg-bull-100 overflow-hidden">
                <div
                  className="h-full transition-all duration-500 bg-bull-500"
                  style={{
                    width: `${debate.bullConviction}%`,
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
                  {debate.bearConviction}%
                </span>
              </div>
              <div className="h-3 rounded-full bg-bear-100 overflow-hidden">
                <div
                  className="h-full transition-all duration-500 bg-bear-500"
                  style={{
                    width: `${debate.bearConviction}%`,
                  }}
                />
              </div>
            </div>

            {/* Total Votes */}
            <div className="mt-lg pt-lg border-t border-border-light text-center text-text-secondary">
              Combined: {debate.bullConviction + debate.bearConviction} votes
            </div>
          </div>
        </div>

        {/* Right: Bear Card */}
        <div>
          <BearCard
            agentName={debate.bearAgent.name}
            argument={debate.bearAgent.argument}
            confidence={debate.bearAgent.confidence}
            metrics={debate.bearAgent.metrics}
            isActive={true}
          />
        </div>
      </div>

      {/* Judge Verdict - Full Width Bottom */}
      <div className="lg:col-span-3">
        <JudgeVerdict
          status={debate.verdict.status}
          tokenPair={debate.verdict.tokenPair}
          winner="bull"
          scoreBreakdown={
            debate.verdict.status === 'revealed'
              ? {
                  bullScore: 78,
                  bearScore: 62,
                  reasoning:
                    'Bull argument presented stronger technical analysis and enterprise adoption data. Sentiment analysis heavily favors bullish positions. However, macroeconomic concerns raised by Bear were valid but lack immediate impact on protocol fundamentals.',
                }
              : undefined
          }
        />
      </div>

      {/* Additional Info Section */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-lg rounded-lg border border-border-light bg-surface p-lg">
        <div>
          <h4 className="font-semibold mb-md text-heading-md text-text-primary">
            About This Debate
          </h4>
          <p className="text-text-secondary text-body-md leading-relaxed">
            This debate is comparing Bull and Bear perspectives on {debate.tokenPair}{' '}
            price movements. Both agents present evidence-based arguments supported
            by technical analysis, market data, and sentiment indicators.
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
    </main>
  );
}
