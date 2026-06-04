import React from 'react';
import { SeverityType } from '../../types';

interface SeverityPillProps {
  severity: SeverityType;
  className?: string;
}

export function SeverityPill({ severity, className = '' }: SeverityPillProps) {
  const styles: Record<SeverityType, string> = {
    critical: 'bg-danger-custom/10 text-danger-custom border border-danger-custom/30',
    high: 'bg-high-custom/10 text-high-custom border border-high-custom/30',
    medium: 'bg-warning-custom/10 text-warning-custom border border-warning-custom/30',
    low: 'bg-glow-blue/10 text-glow-blue border border-glow-blue/30',
    info: 'bg-white/5 text-text-muted border border-border-custom',
  };

  const label: Record<SeverityType, string> = {
    critical: 'CRITICAL',
    high: 'HIGH',
    medium: 'MEDIUM',
    low: 'LOW',
    info: 'INFO',
  };

  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-mono font-semibold tracking-wider ${styles[severity]} ${className}`}>
      {label[severity]}
    </span>
  );
}
