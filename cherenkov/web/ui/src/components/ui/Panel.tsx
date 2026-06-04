import React from 'react';

interface PanelProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
  className?: string;
}

export function Panel({ children, className = '', ...props }: PanelProps) {
  return (
    <div 
      className={`cherenkov-panel rounded-2xl p-6 relative overflow-hidden ${className}`} 
      {...props}
    >
      {children}
    </div>
  );
}
