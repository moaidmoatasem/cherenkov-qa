/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React from 'react';
import { Layers, HelpCircle, HardDrive, DollarSign } from 'lucide-react';
import { Project } from '../types';

interface TopBarProps {
  currentProject: Project | null;
  status: 'Live' | 'Idle';
  activeTab: string;
  totalSpentEstimated: number;
}

export default function TopBar({ 
  currentProject, 
  status, 
  activeTab,
  totalSpentEstimated
}: TopBarProps) {
  
  const getTabLabel = (tab: string) => {
    switch (tab) {
      case 'projects': return 'Project Register';
      case 'setup': return 'Spec Ingest Setup';
      case 'pipeline': return 'Blue Glow Pipeline DAG';
      case 'review': return 'HITL Gate Review';
      case 'healing': return 'API drift self-repair suggestions';
      case 'eject': return 'Playwright Eject Config';
      default: return 'Cherenkov Console';
    }
  };

  return (
    <header className="h-16 border-b border-white/10 bg-black/10 backdrop-blur-md px-6 flex items-center justify-between shrink-0 select-none z-10" id="cherenkov-topbar">
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
      </div>

      {/* Observability Telemetry Indicators */}
      <div className="flex items-center gap-6">
        {/* Token Cost Summary */}
        <div className="flex items-center gap-4 bg-black/30 border border-white/10 px-3.5 py-1.5 rounded-md font-mono text-xs">
          <div className="flex items-center gap-1 text-[#7D8DA1]">
            <DollarSign className="w-3 h-3 text-[#3FB950]" />
            <span>SESSION COST:</span>
          </div>
          <span className="text-glow-bright font-semibold">${totalSpentEstimated.toFixed(2)}</span>
          <span className="text-white/10">|</span>
          <span className="text-[#7D8DA1]/80 text-[10px]">Cloud equivalent: ${(totalSpentEstimated * 3.4).toFixed(3)}</span>
        </div>

        {/* Local Node Status */}
        <div className="flex items-center gap-2">
          <span className="text-[#7D8DA1] uppercase text-[10px] tracking-wider font-mono">NODE STATE:</span>
          <div className="flex items-center gap-1.5 px-3 py-1 rounded bg-white/5 border border-white/10">
            <span className={`w-2 h-2 rounded-full ${status === 'Live' ? 'bg-[#3FB950] animate-pulse' : 'bg-[#7D8DA1]'}`} />
            <span className="text-xs font-mono font-medium text-text-primary uppercase">{status}</span>
          </div>
        </div>

        {/* Dev Reference Utility */}
        <div className="p-1 rounded hover:bg-white/10 cursor-pointer text-[#7D8DA1] hover:text-glow-bright transition" title="Help Guide">
          <HelpCircle className="w-4.5 h-4.5" />
        </div>
      </div>
    </header>
  );
}
