'use client';

import React from 'react';

interface SparklineProps {
  points: string;
  color?: string;
  width?: number;
  height?: number;
}

const Sparkline: React.FC<SparklineProps> = ({ points, color = '#4F46E5', width = 480, height = 80 }) => {
  return (
    <svg width="100%" viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none" className="h-20 w-full">
      <polyline fill="none" stroke={color} strokeWidth={2} points={points} />
    </svg>
  );
};

export default Sparkline;
