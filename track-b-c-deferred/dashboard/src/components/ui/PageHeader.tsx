import React from 'react';

interface PageHeaderProps {
  title: string;
  description?: string;
  primaryAction?: React.ReactNode;
  tabs?: React.ReactNode;
}

export function PageHeader({ title, description, primaryAction, tabs }: PageHeaderProps) {
  return (
    <div className="border-b border-border-custom bg-bg-panel px-6 pt-6 pb-4 flex flex-col gap-4 z-10 relative">
      <div className="flex items-center justify-between gap-4">
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
        {primaryAction && (
          <div className="flex items-center gap-3">
            {primaryAction}
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
