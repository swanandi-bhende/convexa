'use client';

import React from 'react';

interface BearCardProps {
  agentName: string;
  argument: string;
  confidence: number;
  metrics?: {
    label: string;
    value: string;
  }[];
  isActive?: boolean;
}

export const BearCard: React.FC<BearCardProps> = ({
  agentName,
  argument,
  confidence,
  metrics,
  isActive = false,
}) => {
  return (
    <div
      className={`
        flex flex-col h-full rounded-lg border-2 transition-all duration-300
        ${
          isActive
            ? 'border-bear-500 bg-bear-50 shadow-[0_0_20px_rgba(234,88,12,0.2)]'
            : 'border-bear-100 bg-bear-50 bg-opacity-50'
        }
      `}
    >
      {/* Agent Header */}
      <div className="px-lg py-lg border-b border-bear-100 bg-bear-50">
        <div className="flex items-center gap-md mb-md">
          <div className="w-8 h-8 rounded-full flex items-center justify-center font-bold text-white text-label-md bg-bear-500">
            E
          </div>
          <div>
            <h3 className="font-semibold text-body-md text-bear-700">
              {agentName}
            </h3>
            <p className="text-body-sm text-text-secondary">Bear Position</p>
          </div>
        </div>

        {/* Confidence Badge */}
        <div className="flex items-center gap-sm">
          <div className="text-label-md font-semibold text-bear-600">
            {confidence}% Confident
          </div>
          <div className="flex-1 h-2 rounded-full bg-bear-100 overflow-hidden">
            <div
              className="h-full transition-all duration-500 bg-bear-500"
              style={{
                width: `${confidence}%`,
              }}
            />
          </div>
        </div>
      </div>

      {/* Argument Section */}
      <div className="flex-1 px-lg py-lg flex flex-col">
        <p className="flex-1 leading-relaxed text-body-md text-text-primary">
          {argument}
        </p>

        {/* Metrics */}
        {metrics && metrics.length > 0 && (
          <div className="mt-lg pt-lg border-t border-bear-100 grid grid-cols-2 gap-md">
            {metrics.map((metric, idx) => (
              <div key={idx}>
                <p className="text-body-sm text-text-secondary">
                  {metric.label}
                </p>
                <p className="font-semibold text-body-md text-bear-600">
                  {metric.value}
                </p>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Bottom Indicator */}
      <div className="h-1 rounded-b-[5px] bg-bear-500" />
    </div>
  );
};
