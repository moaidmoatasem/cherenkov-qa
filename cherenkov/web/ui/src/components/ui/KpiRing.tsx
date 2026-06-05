import React from 'react';

interface KpiRingProps {
  value: number; // 0 to 100
  title: string;
  subtext?: string;
  size?: number; // width/height in px
  strokeWidth?: number;
  glowColor?: 'blue' | 'success' | 'warning' | 'danger';
}

export function KpiRing({
  value,
  title,
  subtext,
  size = 120,
  strokeWidth = 10,
  glowColor = 'blue',
}: KpiRingProps) {
  const radius = (size - strokeWidth) / 2;
  const circumference = radius * 2 * Math.PI;
  const strokeDashoffset = circumference - (Math.min(100, Math.max(0, value)) / 100) * circumference;

  const colorMap = {
    blue: 'stroke-glow-blue drop-shadow-[0_0_6px_rgba(34,211,238,0.5)]',
    success: 'stroke-success-custom drop-shadow-[0_0_6px_rgba(16,185,129,0.5)]',
    warning: 'stroke-warning-custom drop-shadow-[0_0_6px_rgba(245,158,11,0.5)]',
    danger: 'stroke-danger-custom drop-shadow-[0_0_6px_rgba(239,68,68,0.5)]',
  };

  return (
    <div className="flex flex-col items-center justify-center p-4">
      <div
        className="relative"
        style={{ width: size, height: size }}
        role="progressbar"
        aria-valuenow={value}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={title}
      >
        <svg className="w-full h-full transform -rotate-90">
          {/* Background circle */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            className="stroke-white/5 fill-transparent"
            strokeWidth={strokeWidth}
          />
          {/* Progress circle */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            className={`fill-transparent transition-all duration-500 ease-out ${colorMap[glowColor]}`}
            strokeWidth={strokeWidth}
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
            strokeLinecap="round"
          />
        </svg>
        
        {/* Centered text */}
        <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
          <span className="text-xl font-bold font-mono text-text-primary">
            {value}%
          </span>
          {subtext && (
            <span className="text-[10px] uppercase tracking-wider text-text-muted mt-0.5 px-2 truncate max-w-full">
              {subtext}
            </span>
          )}
        </div>
      </div>
      <span className="text-sm font-semibold text-text-primary mt-3 text-center">
        {title}
      </span>
    </div>
  );
}
