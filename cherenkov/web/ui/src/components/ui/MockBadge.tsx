import React from 'react';
import { AlertTriangle } from 'lucide-react';

export function MockBadge() {
  return (
    <div className="absolute top-4 right-4 z-50 flex items-center gap-1.5 px-3 py-1.5 bg-yellow-500/10 border border-yellow-500/20 text-yellow-400 text-[10px] font-mono font-bold uppercase rounded-full shadow-lg shadow-yellow-500/5 group cursor-help">
      <AlertTriangle className="w-3.5 h-3.5" />
      <span>Mock Data</span>

      {/* Tooltip */}
      <div className="absolute top-full right-0 mt-2 w-64 p-3 bg-slate-900 border border-white/10 rounded-xl shadow-2xl opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none text-left z-50">
        <p className="text-[#E6EDF3] text-xs font-sans normal-case font-normal leading-relaxed">
          This view is currently rendering static mock data for demonstration purposes. It is not connected to a live backend endpoint.
        </p>
      </div>
    </div>
  );
}
