import React from 'react';

interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
  hoverable?: boolean;
  className?: string;
  key?: any;
  onClick?: React.MouseEventHandler<HTMLDivElement>;
}

export function Card({ children, hoverable = false, className = '', ...props }: CardProps) {
  return (
    <div
      className={`cherenkov-card p-5 relative overflow-hidden transition-all duration-200
        ${hoverable ? 'hover:border-glow-blue/40 hover:bg-white/[0.08] hover:shadow-[0_0_15px_rgba(34,211,238,0.15)] cursor-pointer' : ''}
        ${className}`}
      {...props}
    >
      {children}
    </div>
  );
}
