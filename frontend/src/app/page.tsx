'use client';

import React from 'react';
import Link from 'next/link';
import {
  MetricCard,
  MarketSnapshot,
  DebatePreviewCard,
  ConvictionTracker,
  StatsGrid,
} from '@/components';

/**
 * Dashboard landing page with comprehensive overview of platform metrics and active debates
 */
export default function Dashboard() {
  // Mock data - will be replaced with real API data in Step 5
  const recentDebates = [
    {
      id: 1,
      tokenPair: 'ETH/USDC',
      round: 7,
      totalRounds: 10,
      bullScore: 65,
      bearScore: 58,
      status: 'in-progress' as const,
      bullArgument:
        'ETH showing strong recovery with 8.5% weekly gains and increasing institutional adoption',
      bearArgument:
        'Elevated volatility and macro headwinds suggest consolidation phase ahead',
      bullConfidence: 72,
      bearConfidence: 58,
    },
    {
      id: 2,
      tokenPair: 'BTC/USDC',
      round: 3,
      totalRounds: 8,
      bullScore: 71,
      bearScore: 45,
      status: 'in-progress' as const,
      bullArgument: 'Bitcoin approaching key resistance with positive on-chain metrics',
      bearArgument: 'Potential pullback due to profit-taking at current levels',
      bullConfidence: 75,
      bearConfidence: 52,
    },
  ];

  const platformStats = [
    {
      label: 'Total Debates',
      value: '47',
      change: '12 this month',
      changeType: 'up' as const,
    },
    {
      label: 'Active Now',
      value: '3',
      change: 'Last 24 hours',
      changeType: 'neutral' as const,
    },
    {
      label: 'Total Stake',
      value: '285.4 ETH',
      change: '+45.2 ETH',
      changeType: 'up' as const,
    },
    {
      label: 'Avg Accuracy',
      value: '69.8%',
      change: 'Combined agents',
      changeType: 'up' as const,
    },
  ];

  const agentStats = [
    {
      label: 'Bull Win Rate',
      value: '52%',
      change: '18 victories',
      changeType: 'up' as const,
      color: 'bull' as const,
    },
    {
      label: 'Bear Win Rate',
      value: '48%',
      change: '16 victories',
      changeType: 'up' as const,
      color: 'bear' as const,
    },
    {
      label: 'Most Accurate',
      value: 'Bull Agent',
      change: '68.4% accuracy',
      changeType: 'neutral' as const,
    },
    {
      label: 'Avg Confidence',
      value: '64.2%',
      change: 'Across all rounds',
      changeType: 'neutral' as const,
    },
  ];

  return (
    <div className="space-y-3xl">
      {/* Hero Section */}
      <section className="space-y-lg rounded-lg bg-gradient-to-br from-bull-50 via-background to-background border border-bull-500 border-opacity-20 p-xl md:p-3xl">
        <div className="max-w-3xl space-y-md">
          <h1 className="text-display-lg font-bold text-text-primary">
            Autonomous Market Debate Platform
          </h1>
          <p className="text-body-lg text-text-secondary">
            Real-time AI-powered debates between Bull and Bear agents analyzing market movements.
            Watch sophisticated arguments grounded in on-chain data, judge verdicts, and market
            outcomes.
          </p>
          <div className="flex flex-col gap-md sm:flex-row pt-md">
            <Link
              href="/debates/active"
              className="rounded-md bg-bull-500 px-lg py-md text-center text-label-lg font-semibold text-text-inverted transition-colors hover:bg-bull-600 active:bg-bull-700"
            >
              Watch Live Debate
            </Link>
            <Link
              href="/debates/history"
              className="rounded-md border border-bull-500 bg-background px-lg py-md text-center text-label-lg font-semibold text-bull-500 transition-colors hover:bg-bull-50 active:bg-bull-100"
            >
              View Archives
            </Link>
          </div>
        </div>
      </section>

      {/* Platform Overview Stats */}
      <StatsGrid
        title="Platform Overview"
        subtitle="Real-time metrics across all debates and agents"
        stats={platformStats}
        columns={4}
      />

      {/* Featured Live Debate Section */}
      {recentDebates.length > 0 && (
        <section className="space-y-lg">
          <div className="space-y-sm">
            <h2 className="text-heading-lg font-semibold text-text-primary">
              Featured Debate
            </h2>
            <p className="text-body-md text-text-secondary">
              Watch live Bull vs Bear arguments with judge verdicts
            </p>
          </div>

          {/* Main Featured Debate with Conviction Tracker */}
          <div className="grid grid-cols-1 gap-xl lg:grid-cols-3">
            {/* Debate Card */}
            <div className="lg:col-span-2">
              <DebatePreviewCard {...recentDebates[0]} />
            </div>

            {/* Conviction Tracker */}
            <div className="lg:col-span-1">
              <ConvictionTracker
                bullScore={recentDebates[0].bullScore}
                bearScore={recentDebates[0].bearScore}
                winThreshold={70}
                showThreshold={true}
              />
            </div>
          </div>

          {/* Market Snapshot */}
          <div className="grid grid-cols-1 gap-lg lg:grid-cols-2">
            <MarketSnapshot
              tokenPair="ETH/USDC"
              currentPrice={3248.52}
              priceChange24h={8.5}
              volume24h={18500000000}
              volatility={2.4}
              sparkline={[30, 35, 32, 38, 40, 36, 42, 45]}
            />
            <MarketSnapshot
              tokenPair="BTC/USDC"
              currentPrice={63420.75}
              priceChange24h={5.2}
              volume24h={28300000000}
              volatility={1.8}
              sparkline={[28, 32, 35, 38, 36, 40, 42, 44]}
            />
          </div>
        </section>
      )}

      {/* Agent Performance Stats */}
      <StatsGrid
        title="Agent Performance"
        subtitle="Bull and Bear agent metrics and accuracy tracking"
        stats={agentStats}
        columns={4}
      />

      {/* Recent Debates Grid */}
      {recentDebates.length > 1 && (
        <section className="space-y-lg">
          <div className="space-y-sm">
            <h2 className="text-heading-lg font-semibold text-text-primary">
              Recent Debates
            </h2>
            <p className="text-body-md text-text-secondary">
              Latest active and completed debates across token pairs
            </p>
          </div>

          <div className="grid grid-cols-1 gap-md md:grid-cols-2">
            {recentDebates.slice(1).map((debate) => (
              <DebatePreviewCard key={debate.id} {...debate} />
            ))}
          </div>
        </section>
      )}

      {/* Quick Access Cards */}
      <section className="space-y-lg">
        <h2 className="text-heading-lg font-semibold text-text-primary">
          Quick Access
        </h2>
        <div className="grid grid-cols-1 gap-md sm:grid-cols-2 lg:grid-cols-3">
          {[
            {
              title: 'Active Debates',
              description: 'Watch Bull and Bear agents debate in real-time',
              href: '/debates/active',
              color: 'bull',
              count: '3',
            },
            {
              title: 'Debate History',
              description: 'Explore completed debates and market outcomes',
              href: '/debates/history',
              color: 'bear',
              count: '47',
            },
            {
              title: 'Agent Leaderboard',
              description: 'View Bull and Bear agent performance metrics',
              href: '/agents',
              color: 'bull',
              count: '34',
            },
          ].map((link, idx) => (
            <Link
              key={idx}
              href={link.href}
              className={`group rounded-lg border p-lg transition-all duration-200 hover:shadow-lg ${
                link.color === 'bull'
                  ? 'border-bull-500 border-opacity-20 bg-bull-50 hover:bg-bull-100'
                  : 'border-bear-500 border-opacity-20 bg-bear-50 hover:bg-bear-100'
              }`}
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <p
                    className={`text-label-lg font-semibold ${
                      link.color === 'bull'
                        ? 'text-bull-primary'
                        : 'text-bear-primary'
                    }`}
                  >
                    {link.title}
                  </p>
                  <p className="mt-sm text-body-sm text-text-secondary">
                    {link.description}
                  </p>
                </div>
                <div
                  className={`rounded-md px-md py-sm text-label-md font-semibold ${
                    link.color === 'bull'
                      ? 'bg-bull-100 text-bull-primary'
                      : 'bg-bear-100 text-bear-primary'
                  }`}
                >
                  {link.count}
                </div>
              </div>
              <p
                className={`mt-lg text-label-md font-semibold ${
                  link.color === 'bull'
                    ? 'text-bull-primary'
                    : 'text-bear-primary'
                } group-hover:translate-x-xs transition-transform inline-block`}
              >
                Access →
              </p>
            </Link>
          ))}
        </div>
      </section>

      {/* Information Section */}
      <section className="space-y-lg rounded-lg border border-border-light bg-surface p-xl">
        <div className="space-y-md">
          <h2 className="text-heading-lg font-semibold text-text-primary">
            About Convexa
          </h2>
          <div className="space-y-md text-body-md text-text-secondary">
            <p>
              Convexa is an autonomous debate platform where AI agents engage in structured
              economic arguments about token price movements. Bull Agent advocates for bullish
              positions while Bear Agent presents bearish cases—both grounded in real market data.
            </p>
            <p>
              A Judge Agent evaluates both arguments on evidence quality, logic, metric accuracy,
              predictive value, and clarity. Conviction scores update in real-time as verdicts
              arrive, creating a transparent record of agent performance and prediction accuracy.
            </p>
            <p>
              Smart contracts manage staking, settle winners, and track debate histories on Unichain
              Sepolia. Users can watch debates live, review archives, and track agent accuracy over
              time.
            </p>
          </div>
        </div>
      </section>
    </div>
  );
}
