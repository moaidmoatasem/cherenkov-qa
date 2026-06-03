/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React from 'react';
import { 
  FolderGit2, 
  Activity, 
  CheckSquare, 
  Sparkles, 
  Download, 
  Settings, 
  Terminal,
  CircleDot
} from 'lucide-react';
import CherenkovLogo from './CherenkovLogo';

interface SidebarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  onNewRun: () => void;
  status: 'Live' | 'Idle';
  tokenUsagePercent: number;
}

export default function Sidebar({ 
  activeTab, 
  setActiveTab, 
  onNewRun,
  status,
  tokenUsagePercent
}: SidebarProps) {
  
  const navItems = [
    { id: 'projects', label: 'Projects', icon: FolderGit2, desc: 'Registered run workspaces' },
    { id: 'pipeline', label: 'Pipeline Monitor', icon: Activity, desc: 'Live AST pipeline DAG' },
    { id: 'review', label: 'Review Queue', icon: CheckSquare, desc: 'Human-in-the-loop review' },
    { id: 'healing', label: 'Healing Options', icon: Sparkles, desc: 'API Drift & Self-Repair' },
    { id: 'eject', label: 'Eject Suite', icon: Download, desc: 'Export plain Playwright' },
    { id: 'settings', label: 'Settings', icon: Settings, desc: 'Local token & runner budget' },
    { id: 'ui-kit', label: 'UI Kit Gallery', icon: CircleDot, desc: 'Consistency & styling check' },
  ];

  return (
    <aside className="w-[280px] shrink-0 border-r border-white/10 bg-black/20 backdrop-blur-xl flex flex-col justify-between h-full select-none z-10" id="cherenkov-sidebar">
      <div>
        {/* Logo Section */}
        <div className="p-6 border-b border-white/10 flex items-center justify-between">
          <CherenkovLogo variant="full" size={32} />
        </div>

        {/* Action Button */}
        <div className="p-4">
          <button
            onClick={onNewRun}
            id="btn-sidebar-new-run"
            className="w-full h-10 rounded border border-glow-blue/50 bg-cyan-500/10 text-glow-bright text-xs font-semibold uppercase tracking-wider cherenkov-glow hover:bg-glow-blue hover:text-bg-base transition-all duration-300 flex items-center justify-center gap-2"
          >
            <Terminal className="w-4 h-4" />
            <span>New Spec Run</span>
          </button>
        </div>

        {/* Nav Links */}
        <nav className="px-2 py-3 space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                id={`nav-item-${item.id}`}
                onClick={() => setActiveTab(item.id)}
                className={`w-full group px-4 py-3 rounded-lg flex items-start gap-3 transition-all duration-200 text-left relative ${
                  isActive 
                    ? 'bg-white/10 text-glow-bright' 
                    : 'text-[#7D8DA1] hover:text-[#E6EDF3] hover:bg-white/5'
                }`}
              >
                {/* Active left border indicator */}
                {isActive && (
                  <div className="absolute left-0 top-2 bottom-2 w-1 bg-glow-blue rounded-r shadow-[0_0_12px_rgba(34,211,238,0.9)]" />
                )}
                
                <Icon className={`w-5 h-5 shrink-0 mt-0.5 transition-colors ${isActive ? 'text-glow-bright' : 'text-[#7D8DA1] group-hover:text-glow-bright'}`} />
                <div>
                  <span className={`block text-sm font-medium ${isActive ? 'font-semibold text-text-primary text-glow-bright' : 'text-[#7D8DA1]'}`}>
                    {item.label}
                  </span>
                  <span className="block text-[10px] text-[#7D8DA1]/75 mt-0.5 font-normal leading-tight">
                    {item.desc}
                  </span>
                </div>
              </button>
            );
          })}
        </nav>
      </div>

      {/* Bottom Budget Meter / State Display */}
      <div className="p-4 border-t border-white/10 bg-black/30 backdrop-blur-md space-y-4">
        <div>
          <div className="flex justify-between items-center text-[10px] text-[#7D8DA1] font-mono tracking-wider uppercase mb-1.5">
            <span>LLM Token Pool</span>
            <span className="text-glow-bright">{tokenUsagePercent}% Used</span>
          </div>
          <div className="w-full bg-white/5 h-1.5 rounded-full overflow-hidden border border-white/5">
            <div 
              style={{ width: `${tokenUsagePercent}%` }}
              className="bg-glow-blue h-full rounded-full transition-all duration-500 animate-pulse-slow cherenkov-glow"
            />
          </div>
        </div>

        <div className="flex items-center justify-between pt-1 text-[11px] font-mono">
          <div className="flex items-center gap-2">
            <span className={`relative flex h-2 w-2`}>
              <span className={`animate-ping absolute inline-flex h-full w-full rounded-full ${status === 'Live' ? 'bg-glow-bright' : 'bg-[#7D8DA1]'} opacity-75`}></span>
              <span className={`relative inline-flex rounded-full h-2 w-2 ${status === 'Live' ? 'bg-[#3FB950]' : 'bg-[#7D8DA1]'}`}></span>
            </span>
            <span className="text-text-primary">{status === 'Live' ? 'LIVE' : 'IDLE'}</span>
            <span className="text-[#334C5A]">|</span>
            <span className="text-[#7D8DA1]">C-RAD v2.6</span>
          </div>
          <div className="text-[10px] text-[#334C5A]">
            PORT 3000
          </div>
        </div>
      </div>
    </aside>
  );
}
