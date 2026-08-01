import React, { useMemo } from 'react';
import { ShieldCheck, ShieldAlert, ShieldX, Info } from 'lucide-react';

interface EndpointIntegrity {
  id: string;
  path: string;
  method: string;
  integrityScore: number;
  driftCount: number;
}

export default function IntegrityHeatmap({ endpoints }: { endpoints: EndpointIntegrity[] }) {
  const getIntegrityColor = (score: number) => {
    if (score >= 90) return 'bg-[#3FB950] border-[#3FB950]/50 text-white'; // Green
    if (score >= 60) return 'bg-amber-500 border-amber-500/50 text-white'; // Yellow
    return 'bg-red-500 border-red-500/50 text-white'; // Red
  };

  const getIcon = (score: number) => {
    if (score >= 90) return <ShieldCheck className="w-4 h-4 opacity-75" />;
    if (score >= 60) return <ShieldAlert className="w-4 h-4 opacity-75" />;
    return <ShieldX className="w-4 h-4 opacity-75" />;
  };

  const sortedEndpoints = useMemo(() => {
    return [...endpoints].sort((a, b) => a.integrityScore - b.integrityScore);
  }, [endpoints]);

  return (
    <div className="bg-black/20 border border-white/10 rounded-lg p-6 w-full shadow-lg backdrop-blur-sm">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-sm font-semibold text-text-primary flex items-center gap-2">
            Integrity Heatmap
          </h2>
          <p className="text-xs text-text-muted mt-1">At-a-glance coverage & drift score per endpoint</p>
        </div>
        <div className="flex items-center gap-3 text-xs text-text-muted">
          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-[#3FB950]"></span> ≥90%</span>
          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-amber-500"></span> 60-89%</span>
          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-red-500"></span> &lt;60%</span>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
        {sortedEndpoints.map((ep) => (
          <div
            key={ep.id}
            className={`group relative flex flex-col p-3 rounded-lg border transition-all duration-200 hover:scale-105 cursor-pointer shadow-md ${getIntegrityColor(ep.integrityScore)}`}
          >
            <div className="flex items-start justify-between mb-2">
              <span className="text-[10px] font-mono font-bold uppercase tracking-wider bg-black/30 px-1.5 py-0.5 rounded">
                {ep.method}
              </span>
              {getIcon(ep.integrityScore)}
            </div>
            <div className="text-xs font-medium font-mono truncate" title={ep.path}>
              {ep.path}
            </div>
            <div className="mt-2 text-2xl font-bold tracking-tight">
              {ep.integrityScore}%
            </div>

            {/* Tooltip */}
            <div className="absolute opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none -top-12 left-1/2 -translate-x-1/2 bg-gray-900 border border-white/20 shadow-xl rounded px-3 py-2 z-50 min-w-max text-xs text-gray-200 flex flex-col gap-1">
              <span className="font-mono text-cyan-400">{ep.method} {ep.path}</span>
              <span>Integrity: {ep.integrityScore}%</span>
              <span>Drift assertions: {ep.driftCount}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
