/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React from 'react';
import { Layers, HelpCircle, DollarSign, Cpu, Clock } from 'lucide-react';
import { Project } from '../types';
import HealthWidget from './HealthWidget';

interface TopBarProps {
  currentProject: Project | null;
  status: 'Live' | 'Idle';
  activeTab: string;
  totalSpentEstimated: number;
  autonomy: 'Assisted' | 'Augmented' | 'Agentic';
  setAutonomy: (val: 'Assisted' | 'Augmented' | 'Agentic') => void;
  onLiveClick: () => void;
  demoMode?: boolean;
}

export default function TopBar({ 
  currentProject, 
  status, 
  activeTab,
  totalSpentEstimated,
  autonomy,
  setAutonomy,
  onLiveClick,
  demoMode
}: TopBarProps) {
  
  const [sessionTime, setSessionTime] = React.useState(0);

  React.useEffect(() => {
    const interval = setInterval(() => setSessionTime(t => t + 1), 1000);
    return () => clearInterval(interval);
  }, []);

  const formatTime = (seconds: number) => {
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = seconds % 60;
    return `${h > 0 ? h + ':' : ''}${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };
  
  const getTabLabel = (tab: string) => {
    switch (tab) {
      case 'projects': return 'Project Register';
      case 'setup': return 'Spec Ingest Setup';
      case 'pipeline': return 'Blue Glow Pipeline DAG';
      case 'review': return 'HITL Gate Review';
      case 'healing': return 'API drift self-repair suggestions';
      case 'eject': return 'Playwright Eject Config';
      case 'overview': return 'Release Readiness Overview';
      case 'truth-map': return 'Truth Map Claim Graph';
      case 'divergences': return 'Divergence Engine Star';
      case 'explore': return 'Autonomous Explore anomaly list';
      case 'author': return 'Author by Intent manual-QA';
      case 'signals': return 'Telemetry Signals Monitor';
      case 'governance': return 'KPI Certification & Traceability';
      case 'memory': return 'Reflector Memory Pairing';
      case 'ui-kit': return 'UI consistency gallery';
      default: return 'Cherenkov Console';
    }
  };

  return (
    <header className="h-16 border-b border-white/10 bg-black/10 backdrop-blur-md px-6 flex items-center justify-between shrink-0 select-none z-10" id="cherenkov-topbar" data-testid="topbar">
      {/* Current Workspace Breadcrumb */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-1.5 text-xs font-mono text-[#7D8DA1] uppercase tracking-wider">
          <Layers className="w-3.5 h-3.5 text-glow-blue" />
          <span>{currentProject ? currentProject.name : 'NO PROJECT ACTIVE'}</span>
        </div>
        <span className="text-white/10">/</span>
        <span className="text-xs font-semibold text-text-primary px-2.5 py-1 rounded bg-white/5 border border-white/5 uppercase tracking-wider font-sans">
          {getTabLabel(activeTab)}
        </span>
        {demoMode && (
          <span className="ml-2 text-[10px] font-bold px-2 py-1 bg-yellow-500/20 text-yellow-400 border border-yellow-500/50 rounded uppercase animate-pulse">
            Demo data
          </span>
        )}
      </div>

      {/* Autonomy Level Control Segmented Control */}
      <div className="flex items-center gap-2 bg-white/5 border border-white/10 rounded-lg p-0.5" role="radiogroup" aria-label="Autonomy Level Control">
        <span className="text-[10px] font-bold font-mono tracking-wider text-text-muted px-2.5 flex items-center gap-1">
          <Cpu className="w-3 h-3 text-glow-blue" />
          AUTONOMY:
        </span>
        {(['Assisted', 'Augmented', 'Agentic'] as const).map((level) => {
          const isActive = autonomy === level;
          return (
            <button
              key={level}
              role="radio"
              aria-checked={isActive}
              onClick={() => setAutonomy(level)}
              className={`px-3 py-1 rounded-md text-xs font-semibold transition-all cursor-pointer focus-visible:ring-2 focus-visible:ring-glow-blue focus:outline-none
                ${isActive 
                  ? 'bg-glow-blue text-bg-base shadow-[0_0_8px_rgba(34,211,238,0.35)]' 
                  : 'text-text-muted hover:text-text-primary hover:bg-white/5'
                }`}
            >
              {level}
            </button>
          );
        })}
      </div>

      {/* Observability Telemetry Indicators */}
      <div className="flex items-center gap-6">
        {/* Token Cost Summary */}
        <div className="flex items-center gap-4 bg-black/30 border border-white/10 px-3.5 py-1.5 rounded-md font-mono text-xs">
          <div className="flex items-center gap-1 text-[#7D8DA1]" title="Demo telemetry display">
            <DollarSign className="w-3 h-3 text-[#3FB950]" />
            <span>SESSION COST (DEMO):</span>
          </div>
          <span className="text-glow-bright font-semibold">${totalSpentEstimated.toFixed(2)}</span>
          <span className="text-white/10">|</span>
          <span className="text-[#7D8DA1]/80 text-[10px]">Cloud equivalent: ${(totalSpentEstimated * 3.4).toFixed(3)}</span>
        </div>

        {/* Local Node Status (Clickable to open live-run drawer) */}
        <div
          onClick={onLiveClick}
          className="flex items-center gap-2 cursor-pointer group"
          title="Click to view live executing pipeline monitor"
          data-testid="topbar-status"
        >
          <span className="text-[#7D8DA1] group-hover:text-glow-bright uppercase text-[10px] tracking-wider font-mono transition-colors">NODE STATE:</span>
          <div className="flex items-center gap-1.5 px-3 py-1 rounded bg-white/5 border border-white/10 group-hover:border-glow-blue/45 transition-colors">
            <span className={`w-2 h-2 rounded-full ${status === 'Live' ? 'bg-[#3FB950] animate-pulse' : 'bg-[#7D8DA1]'}`} />
            <span className="text-xs font-mono font-medium text-text-primary uppercase">{status}</span>
          </div>
        </div>

        {/* Health Widget */}
        <div data-testid="topbar-health">
          <HealthWidget />
        </div>

        {/* Session Timer */}
        <div className="flex items-center gap-1.5 text-xs font-mono text-[#7D8DA1]">
          <Clock className="w-3.5 h-3.5" />
          <span>{formatTime(sessionTime)}</span>
        </div>

        {/* Notifications - Removed to maintain D7 honesty (no fake text) */}

        {/* Dev Reference Utility */}
        <button
          type="button"
          aria-label="Help Guide"
          className="p-1 rounded hover:bg-white/10 cursor-pointer text-[#7D8DA1] hover:text-glow-bright transition focus-visible:ring-2 focus-visible:ring-glow-blue focus:outline-none"
        >
          <HelpCircle className="w-4.5 h-4.5" />
        </button>
      </div>
    </header>
  );
}
