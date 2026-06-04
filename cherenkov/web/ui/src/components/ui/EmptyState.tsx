import React from 'react';
import { LucideIcon, HelpCircle } from 'lucide-react';
import { Card } from './Card';

interface EmptyStateProps {
  icon?: LucideIcon;
  title: string;
  description: string;
  primaryAction?: {
    label: string;
    onClick: () => void;
  };
  secondaryAction?: {
    label: string;
    onClick: () => void;
  };
  className?: string;
}

export function EmptyState({
  icon: Icon = HelpCircle,
  title,
  description,
  primaryAction,
  secondaryAction,
  className = '',
}: EmptyStateProps) {
  return (
    <Card className={`flex flex-col items-center justify-center text-center p-8 max-w-lg mx-auto ${className}`}>
      <div className="w-12 h-12 rounded-full bg-cyan-950/40 border border-glow-blue/20 flex items-center justify-center mb-4 text-glow-blue">
        <Icon className="w-6 h-6" />
      </div>
      <h3 className="text-lg font-bold font-display text-text-primary mb-2">
        {title}
      </h3>
      <p className="text-sm text-text-muted mb-6 max-w-sm">
        {description}
      </p>
      <div className="flex flex-col sm:flex-row items-center gap-3 w-full sm:w-auto">
        {primaryAction && (
          <button
            onClick={primaryAction.onClick}
            className="w-full sm:w-auto px-4 py-2 text-sm font-semibold rounded-lg bg-glow-blue text-bg-base hover:bg-glow-bright hover:shadow-[0_0_12px_rgba(34,211,238,0.5)] transition-all cursor-pointer"
          >
            {primaryAction.label}
          </button>
        )}
        <button
          onClick={secondaryAction?.onClick || (() => {})}
          className="w-full sm:w-auto px-4 py-2 text-sm font-semibold rounded-lg border border-border-custom bg-white/5 text-text-primary hover:bg-white/10 transition-all cursor-pointer"
        >
          {secondaryAction?.label || 'Try the Petstore demo'}
        </button>
      </div>
    </Card>
  );
}
