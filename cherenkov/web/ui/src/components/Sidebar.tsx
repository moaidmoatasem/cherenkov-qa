/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useMemo } from 'react';
import { 
  FolderGit2, 
  Settings, 
  Terminal,
  CircleDot,
  Cpu,
  LayoutDashboard,
  Network,
  Zap,
  Search,
  Compass,
  CheckSquare,
  TrendingUp,
  Sparkles,
  Download,
  Shield,
  Brain,
  ChevronDown,
  ChevronRight,
  Star,
  MessageSquare,
  Smartphone
} from 'lucide-react';
import CherenkovLogo from './CherenkovLogo';
import { Project } from '../types';

interface SidebarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  onNewRun: () => void;
  status: 'Live' | 'Idle';
  tokenUsagePercent: number;
  projects: Project[];
  selectedProjectId: string | null;
  onSelectProject: (id: string) => void;
}

interface NavSection {
  label: string;
  items: {
    id: string;
    label: string;
    icon: React.ComponentType<any>;
    desc: string;
  }[];
}

export default function Sidebar({ 
  activeTab, 
  setActiveTab, 
  onNewRun,
  status,
  tokenUsagePercent,
  projects,
  selectedProjectId,
  onSelectProject
}: SidebarProps) {
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({
    'OVERVIEW': true,
    'ENGINE': true,
    'AUTHOR': true,
    'SIGNALS': true,
    'OPERATE': true,
    'LEARN': true
  });
  const [searchQuery, setSearchQuery] = useState('');
  const [favorites, setFavorites] = useState<Set<string>>(() => {
    try {
      const saved = localStorage.getItem('[cherenkov] sidebar_favorites');
      return saved ? new Set(JSON.parse(saved) as string[]) : new Set();
    } catch {
      return new Set();
    }
  });

  const toggleSection = (label: string) => {
    setExpandedSections(prev => ({ ...prev, [label]: !prev[label] }));
  };

  const toggleFavorite = (id: string, e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setFavorites(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      try {
        localStorage.setItem('[cherenkov] sidebar_favorites', JSON.stringify([...next]));
      } catch {
        // storage unavailable
      }
      return next;
    });
  };
  
  const sections: NavSection[] = [
    {
      label: 'OVERVIEW',
      items: [
        { id: 'overview', label: 'Overview', icon: LayoutDashboard, desc: 'Release readiness & recent learning' },
      ]
    },
    {
      label: 'ENGINE',
      items: [
        { id: 'truth-map', label: 'Truth Map', icon: Network, desc: 'The endpoint claim graph' },
        { id: 'divergences', label: 'Divergences', icon: Zap, desc: 'Confirmed API inconsistencies' },
        { id: 'explore', label: 'Explore', icon: Search, desc: 'Autonomous explorer digests' },
      ]
    },
    {
      label: 'AUTHOR',
      items: [
        { id: 'author', label: 'Author by Intent', icon: Compass, desc: 'NL-intent interactive Copilot' },
        { id: 'review', label: 'Review Queue', icon: CheckSquare, desc: 'HITL verdict memory gates' },
      ]
    },
    {
      label: 'SIGNALS',
      items: [
        { id: 'signals', label: 'Signals', icon: TrendingUp, desc: 'Visual, Perf & Coverage details' },
      ]
    },
    {
      label: 'OPERATE',
      items: [
        { id: 'healing', label: 'Healing Options', icon: Sparkles, desc: 'API Drift & Self-Repair' },
        { id: 'devices', label: 'Devices', icon: Cpu, desc: 'VLM device management' },
        { id: 'mobile', label: 'Mobile', icon: Smartphone, desc: 'Mobile device testing' },
        { id: 'eject', label: 'Eject Suite', icon: Download, desc: 'Export plain Playwright' },
        { id: 'governance', label: 'Governance', icon: Shield, desc: 'KPI cert & model compliance' },
      ]
    },
    {
      label: 'LEARN',
      items: [
        { id: 'memory', label: 'Memory & Pairing', icon: Brain, desc: 'Reflector senior idioms' },
        { id: 'knowledge', label: 'Knowledge', icon: Brain, desc: 'Second Brain knowledge mesh' },
        { id: 'chat', label: 'Chat', icon: MessageSquare, desc: 'SSE streaming assistant' },
      ]
    }
  ];

  return (
    <aside 
      className="w-20 lg:w-[280px] shrink-0 border-r border-white/10 bg-black/20 backdrop-blur-xl flex flex-col justify-between h-full select-none z-10 transition-all duration-300" 
      id="cherenkov-sidebar"
    >
      <div className="flex flex-col h-full overflow-y-auto">
        {/* Logo Section */}
        <div className="p-4 lg:p-6 border-b border-white/10 flex items-center justify-center lg:justify-between shrink-0">
          <CherenkovLogo variant="full" size={32} className="hidden lg:inline-flex" />
          <CherenkovLogo variant="icon" size={32} className="lg:hidden" />
        </div>

        {/* Action Button */}
        <div className="p-3 lg:p-4 shrink-0">
          <button
            onClick={onNewRun}
            id="btn-sidebar-new-run"
            title="Start New Spec Run"
            className="w-full h-10 rounded border border-glow-blue/50 bg-cyan-500/10 text-glow-bright text-xs font-semibold uppercase tracking-wider cherenkov-glow hover:bg-glow-blue hover:text-bg-base transition-all duration-300 flex items-center justify-center gap-2 cursor-pointer"
          >
            <Terminal className="w-4 h-4 shrink-0" />
            <span className="hidden lg:inline">New Spec Run</span>
          </button>
        </div>

        {/* Search Filter */}
        <div className="px-3 lg:px-4 pb-2 shrink-0 hidden lg:block">
          <div className="relative">
            <Search className="w-3.5 h-3.5 absolute left-2.5 top-2 text-[#7D8DA1]" />
            <input 
              type="text" 
              placeholder="Search..." 
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-black/30 text-text-primary text-xs pl-8 pr-2 py-1.5 rounded border border-white/10 focus:outline-none focus:border-glow-blue transition"
            />
          </div>
        </div>

        {/* Nav Links */}
        <nav className="flex-1 px-2 py-3 space-y-4 overflow-y-auto">
          {sections.map((section) => {
            const filteredItems = section.items.filter(item => 
              item.label.toLowerCase().includes(searchQuery.toLowerCase()) || 
              item.desc.toLowerCase().includes(searchQuery.toLowerCase())
            );
            
            if (filteredItems.length === 0 && searchQuery) return null;

            const isExpanded = expandedSections[section.label];

            return (
              <div key={section.label} className="space-y-1">
                <button 
                  onClick={() => toggleSection(section.label)}
                  className="w-full hidden lg:flex items-center justify-between px-4 text-[10px] font-bold font-mono tracking-widest text-[#7D8DA1]/60 hover:text-[#7D8DA1] transition cursor-pointer"
                >
                  <span>{section.label}</span>
                  {isExpanded ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
                </button>
                {isExpanded && (
                  <div className="space-y-0.5">
                    {filteredItems.map((item) => {
                      const Icon = item.icon;
                      const isActive = activeTab === item.id;
                      return (
                        <button
                          key={item.id}
                          id={`nav-item-${item.id}`}
                          onClick={() => setActiveTab(item.id)}
                          title={`${item.label} — ${item.desc}`}
                          className={`w-full group px-3 lg:px-4 py-2.5 rounded-lg flex items-center lg:items-start gap-3 transition-all duration-200 text-left relative focus:outline-none focus:ring-1 focus:ring-glow-blue/50 cursor-pointer ${
                            isActive 
                              ? 'bg-white/10 text-glow-bright' 
                              : 'text-[#7D8DA1] hover:text-[#E6EDF3] hover:bg-white/5'
                          }`}
                        >
                          {isActive && (
                            <div className="absolute left-0 top-1.5 bottom-1.5 w-1 bg-glow-blue rounded-r shadow-[0_0_12px_rgba(34,211,238,0.9)]" />
                          )}
                          <Icon className={`w-5 h-5 shrink-0 transition-colors ${isActive ? 'text-glow-bright' : 'text-[#7D8DA1] group-hover:text-glow-bright'}`} />
                          <div className="hidden lg:block min-w-0">
                            <span className={`block text-sm font-medium ${isActive ? 'font-semibold text-text-primary text-glow-bright' : 'text-[#7D8DA1]'}`}>
                              {item.label}
                            </span>
                            <span className="block text-[10px] text-[#7D8DA1]/75 mt-0.5 font-normal leading-tight truncate">
                              {item.desc}
                            </span>
                          </div>
                        </button>
                      );
                    })}
                  </div>
                )}
              </div>
            );
          })}
        </nav>
      </div>

      {/* Bottom Pinned section */}
      <div className="p-3 lg:p-4 border-t border-white/10 bg-black/30 backdrop-blur-md space-y-4 shrink-0">
        {/* Project Switcher Selector */}
        <div className="flex flex-col gap-1.5">
          <label htmlFor="project-selector" className="hidden lg:block text-[9px] font-bold font-mono tracking-wider uppercase text-[#7D8DA1]">
            Active Workspace
          </label>
          <div className="relative bg-white/5 border border-white/10 rounded-lg hidden lg:block">
            <div className="flex items-center gap-2 p-1.5">
              <FolderGit2 className="w-4 h-4 text-glow-blue shrink-0 ml-1" />
              <select
                id="project-selector"
                name="project-selector"
                aria-label="Active Workspace"
                value={selectedProjectId || ''}
                onChange={(e) => onSelectProject(e.target.value)}
                className="bg-transparent text-xs text-text-primary focus:outline-none w-full cursor-pointer font-sans appearance-none pr-6"
              >
                {projects.map((p) => (
                  <option key={p.id} value={p.id} className="bg-bg-base text-text-primary">
                    {favorites.has(p.id) ? '★ ' : ''}{p.name}
                  </option>
                ))}
              </select>
              {selectedProjectId && (
                <button 
                  onClick={(e) => toggleFavorite(selectedProjectId, e)}
                  className="absolute right-2 top-1/2 -translate-y-1/2 p-1 hover:bg-white/10 rounded text-[#7D8DA1] hover:text-yellow-400 transition"
                  title="Toggle Favorite"
                >
                  <Star className={`w-3.5 h-3.5 ${favorites.has(selectedProjectId) ? 'fill-yellow-400 text-yellow-400' : ''}`} />
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Settings button */}
        <button
          onClick={() => setActiveTab('settings')}
          title="Open Settings"
          className={`w-full group px-3 lg:px-4 py-2 rounded-lg flex items-center gap-3 transition-colors cursor-pointer focus:outline-none focus:ring-1 focus:ring-glow-blue/50 ${
            activeTab === 'settings' 
              ? 'bg-white/10 text-glow-bright' 
              : 'text-[#7D8DA1] hover:text-[#E6EDF3] hover:bg-white/5'
          }`}
        >
          <Settings className="w-5 h-5 shrink-0" />
          <span className="hidden lg:inline text-sm font-medium">Settings</span>
        </button>

        {/* UI Kit gallery — dev builds only */}
        {import.meta.env.DEV && (
          <button
            onClick={() => setActiveTab('ui-kit')}
            title="Open UI Kit Gallery"
            className={`w-full group px-3 lg:px-4 py-2 rounded-lg flex items-center gap-3 transition-colors cursor-pointer focus:outline-none focus:ring-1 focus:ring-glow-blue/50 ${
              activeTab === 'ui-kit'
                ? 'bg-white/10 text-glow-bright'
                : 'text-[#7D8DA1] hover:text-[#E6EDF3] hover:bg-white/5'
            }`}
          >
            <CircleDot className="w-5 h-5 shrink-0" />
            <span className="hidden lg:inline text-sm font-medium">UI Kit Gallery</span>
          </button>
        )}

        {/* Budget bar */}
        <div className="hidden lg:block">
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

        {/* Status ring */}
        <div className="flex items-center justify-center lg:justify-between pt-1 text-[11px] font-mono">
          <div className="flex items-center gap-2">
            <span className={`relative flex h-2 w-2`}>
              <span className={`animate-ping absolute inline-flex h-full w-full rounded-full ${status === 'Live' ? 'bg-glow-bright' : 'bg-[#7D8DA1]'} opacity-75`}></span>
              <span className={`relative inline-flex rounded-full h-2 w-2 ${status === 'Live' ? 'bg-[#3FB950]' : 'bg-[#7D8DA1]'}`}></span>
            </span>
            <span className="hidden lg:inline text-text-primary">{status === 'Live' ? 'LIVE' : 'IDLE'}</span>
          </div>
          <span className="hidden lg:inline text-[10px] text-[#334C5A]">PORT {import.meta.env.VITE_PORT || '3000'}</span>
        </div>
      </div>
    </aside>
  );
}
