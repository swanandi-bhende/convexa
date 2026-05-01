'use client';

import React from 'react';

interface MetricCardProps {
  label: string;
  value: string;
  trend?: string;
  trendDirection?: 'up' | 'down' | 'neutral';
  icon?: React.ReactNode;
  highlight?: boolean;
}

/**
 * Metric Card component for displaying key performance indicators
 */
export const MetricCard: React.FC<MetricCardProps> = ({
  label,
  value,
  trend,
  trendDirection = 'neutral',
  icon,
  highlight = false,
}) => {
  const trendColor = {
    up: 'text-success-500',
    down: 'text-error-500',
    neutral: 'text-text-secondary',
  }[trendDirection];

  return (
    <div
      className={`rounded-lg border transition-all duration-200 hover:shadow-lg ${
        highlight
          ? 'border-bull-500 bg-bull-50'
          : 'border-border-light bg-surface'
      } p-lg`}
    >
      {/* Header */}
      <div className="flex items-start justify-between">
        <p
          className={`text-body-sm font-medium ${
            highlight ? 'text-bull-primary' : 'text-text-tertiary'
          }`}
        >
          {label}
        </p>
        {icon && (
          <div
            className={`rounded-md p-sm ${
              highlight ? 'bg-bull-100' : 'bg-surface-tertiary'
            }`}
          >
            {icon}
          </div>
        )}
      </div>

      {/* Value */}
      <p
        className={`mt-md text-heading-md font-semibold ${
          highlight ? 'text-bull-primary' : 'text-text-primary'
        }`}
      >
        {value}
      </p>

      {/* Trend */}
      {trend && (
        <p className={`mt-sm text-body-sm font-medium ${trendColor}`}>
          {trend}
        </p>
      )}
    </div>
  );
};
