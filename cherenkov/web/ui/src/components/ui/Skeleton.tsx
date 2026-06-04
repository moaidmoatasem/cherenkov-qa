import React from 'react';
import { useReducedMotion } from '../../lib/useReducedMotion';

interface SkeletonProps {
  variant?: 'text' | 'rect' | 'circle' | 'card' | 'list';
  className?: string;
}

export function Skeleton({ variant = 'text', className = '' }: SkeletonProps) {
  const isReduced = useReducedMotion();
  const animationClass = isReduced ? '' : 'animate-pulse';

  if (variant === 'list') {
    return (
      <div className="flex flex-col gap-3 w-full">
        <Skeleton variant="text" className="w-1/4 h-5" />
        <Skeleton variant="rect" className="w-full h-12" />
        <Skeleton variant="rect" className="w-full h-12" />
        <Skeleton variant="rect" className="w-full h-12" />
      </div>
    );
  }

  if (variant === 'card') {
    return (
      <div className="cherenkov-card p-5 flex flex-col gap-4 w-full">
        <div className="flex items-center gap-3">
          <Skeleton variant="circle" className="w-10 h-10" />
          <div className="flex-1 flex flex-col gap-2">
            <Skeleton variant="text" className="w-1/3 h-4" />
            <Skeleton variant="text" className="w-1/2 h-3" />
          </div>
        </div>
        <Skeleton variant="rect" className="w-full h-24" />
      </div>
    );
  }

  const baseClasses = `bg-white/5 border border-white/5 ${animationClass} ${className}`;

  if (variant === 'circle') {
    return <div className={`rounded-full ${baseClasses}`} />;
  }

  if (variant === 'rect') {
    return <div className={`rounded-xl ${baseClasses}`} />;
  }

  // default is text line
  return <div className={`h-4 w-full rounded ${baseClasses}`} />;
}
