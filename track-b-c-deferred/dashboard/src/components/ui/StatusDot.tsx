import React from 'react';
import { useReducedMotion } from '../../lib/useReducedMotion';

export type StatusType = 'reproduced' | 'pending' | 'rejected' | 'live';

interface StatusDotProps {
  status: StatusType;
  showLabel?: boolean;
  className?: string;
}

export function StatusDot({ status, showLabel = false, className = '' }: StatusDotProps) {
  const isReduced = useReducedMotion();

  const config: Record<StatusType, { dotClass: string; label: string }> = {
    reproduced: {
      dotClass: 'bg-success-custom shadow-[0_0_8px_rgba(16,185,129,0.4)]',
      label: 'Reproduced',
    },
    pending: {
      dotClass: 'bg-warning-custom shadow-[0_0_8px_rgba(245,158,11,0.4)]',
      label: 'Pending',
    },
    rejected: {
      dotClass: 'bg-gray-brand border border-border-custom',
      label: 'Rejected',
    },
    live: {
      dotClass: `bg-glow-blue shadow-[0_0_10px_rgba(34,211,238,0.6)] ${!isReduced ? 'animate-pulse' : ''}`,
      label: 'Live',
    },
  };

  return (
    <span className={`inline-flex items-center gap-2 ${className}`}>
      <span className={`w-2.5 h-2.5 rounded-full ${config[status].dotClass}`} />
      {showLabel && (
        <span className="text-xs font-mono font-medium text-text-primary">
          {config[status].label}
        </span>
      )}
    </span>
  );
}
