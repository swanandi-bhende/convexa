'use client';

import React from 'react';
import Link from 'next/link';

/**
 * Dashboard landing page with metrics, latest debates, and calls-to-action
 */
export default function Dashboard() {
  // Mock data - will be replaced with real data in Step 5
  const metrics = [
    { label: 'Active Debates', value: '3', trend: '+2 this week' },
    { label: 'Total Stake', value: '15.4 ETH', trend: '+3.2 ETH this week' },
    { label: 'Bull Accuracy', value: '68.5%', trend: 'Last 10 rounds' },
    { label: 'Bear Accuracy', value: '71.2%', trend: 'Last 10 rounds' },
  ];

  const latestDebate = {
    id: 1,
    tokenPair: 'ETH/USDC',
    round: 5,
    totalRounds: 10,
    bullScore: 62,
    bearScore: 58,
    status: 'in-progress' as const,
  };

  return (
    <div className="space-y-2xl">
      {/* Hero Section */}
      <section className="space-y-lg rounded-lg bg-gradient-to-br from-bull-50 to-background p-xl md:p-3xl">
        <div className="space-y-md max-w-2xl">
          <h1 className="text-display-lg font-bold text-text-primary">
            Welcome to Convexa
          </h1>
          <p className="text-body-lg text-text-secondary">
            Watch autonomous AI agents debate market movements in real-time. Bull
            vs Bear. Facts vs Data. Predictions vs Reality.
          </p>
          <div className="flex flex-col gap-md sm:flex-row">
            <Link
              href="/debates/active"
              className="rounded-md bg-bull-500 px-lg py-md text-label-lg font-semibold text-text-inverted transition-colors hover:bg-bull-600"
            >
              Watch Debate Now
            </Link>
            <button
              className="rounded-md border border-bull-500 px-lg py-md text-label-lg font-semibold text-bull-500 transition-colors hover:bg-bull-50"
            >
              Learn More
            </button>
          </div>
        </div>
      </section>

      {/* Key Metrics Cards */}
      <section className="space-y-md">
        <h2 className="text-heading-lg font-semibold text-text-primary">
          Platform Metrics
        </h2>
        <div className="grid grid-cols-1 gap-md md:grid-cols-2 lg:grid-cols-4">
          {metrics.map((metric, idx) => (
            <div
              key={idx}
              className="surface-default space-y-sm rounded-lg border border-border-light bg-surface p-lg transition-shadow hover:shadow-md"
            >
              <p className="text-body-sm text-text-tertiary">{metric.label}</p>
              <p className="text-heading-md font-semibold text-text-primary">
                {metric.value}
              </p>
              <p className="text-body-sm text-text-secondary">{metric.trend}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Latest Debate Summary */}
      <section className="space-y-md">
        <h2 className="text-heading-lg font-semibold text-text-primary">
          Current Debate
        </h2>
        <div className="surface-default rounded-lg border border-border-light bg-surface p-xl md:p-2xl">
          <div className="space-y-lg">
            {/* Header */}
            <div className="flex flex-col items-start justify-between gap-md sm:flex-row sm:items-center">
              <div>
                <p className="text-label-lg font-semibold text-text-primary">
                  {latestDebate.tokenPair}
                </p>
                <p className="text-body-sm text-text-secondary">
                  Round {latestDebate.round} of {latestDebate.totalRounds}
                </p>
              </div>
              <span className="inline-flex rounded-full bg-success-50 px-md py-sm text-label-md font-semibold text-success-500">
                Live
              </span>
            </div>

            {/* Score Bars */}
            <div className="space-y-lg">
              {/* Bull Score */}
              <div className="space-y-sm">
                <div className="flex items-center justify-between">
                  <p className="text-label-md font-semibold text-bull-500">
                    Bull Position
                  </p>
                  <p className="text-label-md font-semibold text-text-primary">
                    {latestDebate.bullScore}/100
                  </p>
                </div>
                <div className="h-3 w-full overflow-hidden rounded-full bg-border-light">
                  <div
                    className="h-full bg-bull-500 transition-all duration-500"
                    style={{
                      width: `${latestDebate.bullScore}%`,
                    }}
                  />
                </div>
              </div>

              {/* Bear Score */}
              <div className="space-y-sm">
                <div className="flex items-center justify-between">
                  <p className="text-label-md font-semibold text-bear-500">
                    Bear Position
                  </p>
                  <p className="text-label-md font-semibold text-text-primary">
                    {latestDebate.bearScore}/100
                  </p>
                </div>
                <div className="h-3 w-full overflow-hidden rounded-full bg-border-light">
                  <div
                    className="h-full bg-bear-500 transition-all duration-500"
                    style={{
                      width: `${latestDebate.bearScore}%`,
                    }}
                  />
                </div>
              </div>
            </div>

            {/* Call-to-Action */}
            <div className="flex flex-col gap-md pt-lg sm:flex-row">
              <Link
                href={`/debates/active`}
                className="flex-1 rounded-md bg-bull-500 px-lg py-md text-center text-label-lg font-semibold text-text-inverted transition-colors hover:bg-bull-600"
              >
                View Full Debate
              </Link>
              <button className="flex-1 rounded-md border border-border-light bg-background px-lg py-md text-label-lg font-semibold text-bull-500 transition-colors hover:bg-surface">
                View Details
              </button>
            </div>
          </div>
        </div>
      </section>

      {/* Quick Links Section */}
      <section className="space-y-md">
        <h2 className="text-heading-lg font-semibold text-text-primary">
          Get Started
        </h2>
        <div className="grid grid-cols-1 gap-md sm:grid-cols-2 lg:grid-cols-3">
          {[
            {
              title: 'Watch Debates',
              description: 'View live debates between Bull and Bear agents',
              href: '/debates/active',
              color: 'bull',
            },
            {
              title: 'View History',
              description: 'Explore past debates and track market outcomes',
              href: '/debates/history',
              color: 'bear',
            },
            {
              title: 'Agent Stats',
              description: 'Check Bull and Bear accuracy and performance metrics',
              href: '/agents',
              color: 'bull',
            },
          ].map((link, idx) => (
            <Link
              key={idx}
              href={link.href}
              className={`group rounded-lg border border-border-light p-lg transition-all hover:shadow-lg ${
                link.color === 'bull'
                  ? 'bg-bull-50 hover:bg-bull-100'
                  : 'bg-bear-50 hover:bg-bear-100'
              }`}
            >
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
              <p
                className={`mt-md text-label-md font-semibold ${
                  link.color === 'bull'
                    ? 'text-bull-primary'
                    : 'text-bear-primary'
                } group-hover:translate-x-xs transition-transform`}
              >
                Learn more →
              </p>
            </Link>
          ))}
        </div>
      </section>
    </div>
  );
}
