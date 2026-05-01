'use client';

import React from 'react';

interface MarketSnapshotProps {
  tokenPair: string;
  currentPrice: number;
  priceChange24h: number;
  volume24h: number;
  volatility: number;
  timestamp?: string;
  sparkline?: number[];
}

/**
 * Market Snapshot component displaying current market data
 */
export const MarketSnapshot: React.FC<MarketSnapshotProps> = ({
  tokenPair,
  currentPrice,
  priceChange24h,
  volume24h,
  volatility,
  timestamp = 'Real-time',
  sparkline,
}) => {
  const isPriceUp = priceChange24h >= 0;
  const priceChangeClass = isPriceUp ? 'text-success-500' : 'text-error-500';
  const priceChangeBgClass = isPriceUp ? 'bg-success-50' : 'bg-error-50';

  const formatPrice = (price: number) => {
    return `$${price.toLocaleString('en-US', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    })}`;
  };

  const formatVolume = (vol: number) => {
    if (vol >= 1e9) return `$${(vol / 1e9).toFixed(2)}B`;
    if (vol >= 1e6) return `$${(vol / 1e6).toFixed(2)}M`;
    if (vol >= 1e3) return `$${(vol / 1e3).toFixed(2)}K`;
    return `$${vol.toFixed(0)}`;
  };

  return (
    <div className="rounded-lg border border-border-light bg-surface p-lg">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <p className="text-label-lg font-semibold text-text-primary">
            {tokenPair}
          </p>
          <p className="text-body-sm text-text-tertiary">{timestamp}</p>
        </div>
        <div className="text-right">
          <p className="text-heading-md font-semibold text-text-primary">
            {formatPrice(currentPrice)}
          </p>
        </div>
      </div>

      {/* Price Change Indicator */}
      <div
        className={`mt-lg rounded-md ${priceChangeBgClass} px-md py-sm inline-flex items-center gap-sm`}
      >
        <svg
          className={`h-4 w-4 ${priceChangeClass} ${
            isPriceUp ? '' : 'rotate-180'
          }`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M13 7l5 5m0 0l-5 5m5-5H6"
          />
        </svg>
        <span className={`text-label-md font-semibold ${priceChangeClass}`}>
          {isPriceUp ? '+' : ''}{priceChange24h.toFixed(2)}%
        </span>
      </div>

      {/* Market Stats Grid */}
      <div className="mt-lg grid grid-cols-2 gap-md">
        {/* Volume */}
        <div className="space-y-xs">
          <p className="text-body-sm text-text-tertiary">24h Volume</p>
          <p className="text-label-lg font-semibold text-text-primary">
            {formatVolume(volume24h)}
          </p>
        </div>

        {/* Volatility */}
        <div className="space-y-xs">
          <p className="text-body-sm text-text-tertiary">Volatility</p>
          <div className="flex items-end gap-sm">
            <p className="text-label-lg font-semibold text-text-primary">
              {volatility.toFixed(2)}%
            </p>
            <div className="flex h-4 gap-xs">
              {[...Array(5)].map((_, i) => (
                <div
                  key={i}
                  className={`w-1 rounded-full ${
                    i < Math.ceil(volatility / 20)
                      ? 'bg-warning-500'
                      : 'bg-border-light'
                  }`}
                  style={{
                    height: `${8 + i * 2}px`,
                  }}
                />
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Sparkline (if provided) */}
      {sparkline && sparkline.length > 0 && (
        <div className="mt-lg">
          <svg className="h-12 w-full" viewBox="0 0 100 40" preserveAspectRatio="none">
            <polyline
              points={sparkline
                .map((value, i) => `${(i / (sparkline.length - 1)) * 100},${40 - (value * 30)}`)
                .join(' ')}
              fill="none"
              stroke={isPriceUp ? '#16a34a' : '#dc2626'}
              strokeWidth="0.5"
            />
          </svg>
        </div>
      )}
    </div>
  );
};
