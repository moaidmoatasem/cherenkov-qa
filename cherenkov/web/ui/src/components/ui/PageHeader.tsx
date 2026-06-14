import React from 'react';

interface PageHeaderProps {
  title: string;
  description?: string;
  primaryAction?: React.ReactNode | { label: string; onClick?: () => void; testId?: string };
  tabs?: React.ReactNode;
}

export function PageHeader({ title, description, primaryAction, tabs }: PageHeaderProps) {
  let actionElement: React.ReactNode = null;

  if (primaryAction) {
    if (typeof primaryAction === 'object' && 'label' in primaryAction) {
      const act = primaryAction as { label: string; onClick?: () => void; testId?: string };
      actionElement = (
        <button
          onClick={act.onClick}
          data-testid={act.testId}
          className="px-4 py-2 bg-glow-blue hover:bg-opacity-90 text-slate-950 font-bold text-xs rounded-xl uppercase tracking-wider transition-all duration-300 cursor-pointer shadow-lg shadow-cyan-500/10"
        >
          {act.label}
        </button>
      );
    } else {
      actionElement = primaryAction as React.ReactNode;
    }
  }

  return (
    <div className="border-b border-border-custom bg-bg-panel px-6 pt-6 pb-4 flex flex-col gap-4 z-10 relative">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div className="flex flex-col gap-1">
          <h1 className="text-2xl font-bold font-display text-text-primary tracking-tight">
            {title}
          </h1>
          {description && (
            <p className="text-sm text-text-muted">
              {description}
            </p>
          )}
        </div>
        {actionElement && (
          <div className="flex items-center gap-3">
            {actionElement}
          </div>
        )}
      </div>
      {tabs && (
        <div className="mt-2">
          {tabs}
        </div>
      )}
    </div>
  );
}
