'use client';

import React from 'react';

interface StatItem {
  label: string;
  value: string;
  change?: string;
  changeType?: 'up' | 'down' | 'neutral';
  color?: 'bull' | 'bear' | 'default';
}

interface StatsGridProps {
  title: string;
  subtitle?: string;
  stats: StatItem[];
  columns?: 2 | 3 | 4;
}

/**
 * Stats Grid component for displaying multiple metrics in a grid layout
 */
export const StatsGrid: React.FC<StatsGridProps> = ({
  title,
  subtitle,
  stats,
  columns = 4,
}) => {
  const getColorClass = (color?: string) => {
    switch (color) {
      case 'bull':
        return 'border-bull-500 border-opacity-20 bg-bull-50';
      case 'bear':
        return 'border-bear-500 border-opacity-20 bg-bear-50';
      default:
        return 'border-border-light bg-surface';
    }
  };

  const getChangeColor = (changeType?: string) => {
    switch (changeType) {
      case 'up':
        return 'text-success-500';
      case 'down':
        return 'text-error-500';
      default:
        return 'text-text-secondary';
    }
  };

  const gridColsClass = {
    2: 'grid-cols-1 sm:grid-cols-2',
    3: 'grid-cols-1 sm:grid-cols-2 lg:grid-cols-3',
    4: 'grid-cols-1 sm:grid-cols-2 lg:grid-cols-4',
  }[columns];

  return (
    <section className="space-y-lg">
      {/* Header */}
      <div className="space-y-sm">
        <h2 className="text-heading-lg font-semibold text-text-primary">
          {title}
        </h2>
        {subtitle && (
          <p className="text-body-md text-text-secondary">{subtitle}</p>
        )}
      </div>

      {/* Stats Grid */}
      <div className={`grid ${gridColsClass} gap-md`}>
        {stats.map((stat, idx) => (
          <div
            key={idx}
            className={`rounded-lg border p-lg transition-all duration-200 hover:shadow-md ${getColorClass(stat.color)}`}
          >
            <p className="text-body-sm font-medium text-text-tertiary">
              {stat.label}
            </p>
            <p className="mt-sm text-heading-md font-semibold text-text-primary">
              {stat.value}
            </p>
            {stat.change && (
              <p
                className={`mt-sm text-body-sm font-semibold ${getChangeColor(stat.changeType)}`}
              >
                {stat.changeType === 'up' && '+'}
                {stat.change}
              </p>
            )}
          </div>
        ))}
      </div>
    </section>
  );
};
