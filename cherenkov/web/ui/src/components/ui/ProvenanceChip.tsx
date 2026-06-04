import React from 'react';
import { FileJson, Code, Activity, Database } from 'lucide-react';

export type ProvenanceType = 'spec' | 'code' | 'traffic' | 'db';

interface ProvenanceChipProps {
  type: ProvenanceType;
  className?: string;
}

export function ProvenanceChip({ type, className = '' }: ProvenanceChipProps) {
  const styles: Record<ProvenanceType, { container: string; icon: React.ReactNode; label: string }> = {
    spec: {
      container: 'bg-blue-500/10 text-blue-400 border border-blue-500/20',
      icon: <FileJson className="w-3.5 h-3.5" />,
      label: 'spec',
    },
    code: {
      container: 'bg-purple-500/10 text-purple-400 border border-purple-500/20',
      icon: <Code className="w-3.5 h-3.5" />,
      label: 'code',
    },
    traffic: {
      container: 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20',
      icon: <Activity className="w-3.5 h-3.5" />,
      label: 'traffic',
    },
    db: {
      container: 'bg-amber-500/10 text-amber-400 border border-amber-500/20',
      icon: <Database className="w-3.5 h-3.5" />,
      label: 'db',
    },
  };

  const current = styles[type];

  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded text-xs font-mono font-medium ${current.container} ${className}`}>
      {current.icon}
      {current.label}
    </span>
  );
}
