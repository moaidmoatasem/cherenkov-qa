/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useEffect, useState } from 'react';
import CherenkovLogo from '../CherenkovLogo';
import { Project } from '../../types';
import { fetchProjects, fetchMetricsData, checkBackendHealth, fetchSettings, SystemSettings } from '../../lib/api';
import { ChevronDown, RefreshCw, Cpu, Activity, Shield, Zap, Settings, Menu, X } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

interface AppHeaderProps {
  activeWorkspaceTitle: string;
  activeWorkspaceSubtitle?: string;
  selectedProjectId: string | null;
  onSelectProject: (projectId: string) => void;
  tokenUsagePercent?: number;
  totalSpentEstimated?: number;
  online?: boolean;
  /** Mobile nav drawer controls. Hidden from lg up, where the sidebar is static. */
  navOpen?: boolean;
  onToggleNav?: () => void;
}

export const AppHeader: React.FC<AppHeaderProps> = ({
  activeWorkspaceTitle,
  activeWorkspaceSubtitle = 'Autonomous API Conformance & QA Engine',
  selectedProjectId,
  onSelectProject,
  tokenUsagePercent = 0,
  totalSpentEstimated = 0,
  online = true,
  navOpen = false,
  onToggleNav,
}) => {
  const [projects, setProjects] = useState<Project[]>([]);
  const [settings, setSettings] = useState<SystemSettings | null>(null);
  const [isHealthChecking, setIsHealthChecking] = useState(false);
  const [isHealthOnline, setIsHealthOnline] = useState<boolean>(online);
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    setIsHealthOnline(online);
  }, [online]);

  useEffect(() => {
    fetchProjects()
      .then((data) => {
        setProjects(data || []);
      })
      .catch(() => {
        setProjects([]);
      });

    const pollSettings = () => {
      fetchSettings()
        .then((data) => setSettings(data))
        .catch(() => {});
    };
    pollSettings();
    const id = setInterval(pollSettings, 15000);
    return () => clearInterval(id);
  }, [selectedProjectId]);

  const handleManualHealthCheck = async () => {
    setIsHealthChecking(true);
    try {
      const res = await checkBackendHealth();
      setIsHealthOnline(res);
    } catch {
      setIsHealthOnline(false);
    } finally {
      setIsHealthChecking(false);
    }
  };

  const currentProject = projects.find((p) => p.id === selectedProjectId);

  return (
    <header className="ds-header">
      {/* Brand & Active Workspace Context */}
      <div className="ds-flex-row ds-gap-lg">
        {onToggleNav && (
          <button
            type="button"
            onClick={onToggleNav}
            aria-expanded={navOpen}
            aria-controls="primary-navigation"
            aria-label={navOpen ? 'Close navigation' : 'Open navigation'}
            data-testid="nav-drawer-toggle"
            className="lg:hidden p-2 -ml-1 rounded-lg text-text-primary hover:bg-white/10 transition shrink-0"
          >
            {navOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        )}
        <div className="ds-flex-row ds-gap-sm">
          {/* `variant` defaults to "full", which renders the CHERENKOV /
              THE FORENSIC QA PROTOCOL wordmark. Inside this 28px box that text
              overflowed and sat on top of the "CHERENKOV QA" title beside it,
              swallowing pointer events across the header. The header already
              spells out the name, so the mark only needs the icon. */}
          <CherenkovLogo
            variant="icon"
            size={28}
            className="w-7 h-7 pointer-events-none"
            style={{ color: 'var(--primary)' }}
          />
          <div className="ds-flex-col">
            <span className="ds-title ds-text-gradient ds-flex-row ds-gap-sm">
              CHERENKOV <span style={{ fontSize: '10px', padding: '2px 6px', borderRadius: '4px', background: 'rgba(14, 165, 233, 0.1)', border: '1px solid rgba(14, 165, 233, 0.2)' }}>QA</span>
            </span>
          </div>
        </div>

        <div className="hidden md:block" style={{ width: '1px', height: '24px', background: 'var(--border-glass)' }} />

        {/* Workspace Title — persistent chrome, and a duplicate of the same
            title rendered by each workspace's PageHeader. Two h1s carrying the
            same text give a screen-reader user two competing page headings, so
            this one is a plain element (identical classes, no visual change)
            and the one inside the main content stays the page's single h1. */}
        {/* Redundant on narrow screens -- the workspace renders the same
            title as its own h1 -- and it was pushing the header off-screen. */}
        <div className="hidden md:block min-w-0">
          <div className="ds-title ds-flex-row ds-gap-sm" aria-hidden="true">
            {activeWorkspaceTitle}
          </div>
          <p className="ds-subtitle" aria-hidden="true">{activeWorkspaceSubtitle}</p>
        </div>
      </div>

      {/* Center/Right Status Controls */}
      <div className="ds-flex-row ds-gap-md">
        {/* Active Project Dropdown Selector */}
        <div className="relative">
          <button
            onClick={() => setIsDropdownOpen(!isDropdownOpen)}
            className="ds-button ds-glass-panel"
            data-testid="project-selector-dropdown"
            title="Workspace selection is cosmetic in this build: it highlights a project here but does not filter backend data, which is global until project-scoped APIs ship."
          >
            <span style={{ color: 'var(--text-muted)' }}>Project:</span>
            <span className="ds-text-gradient" style={{ maxWidth: '140px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {currentProject ? currentProject.name : 'Select Project'}
            </span>
            <ChevronDown className="w-3.5 h-3.5" style={{ color: 'var(--text-muted)' }} />
          </button>

          {isDropdownOpen && (
            <div className="absolute right-0 mt-2 w-64 rounded-xl bg-bg-surface border border-border-strong shadow-2xl z-50 py-2">
              <div className="px-3 py-1.5 border-b border-border-subtle text-[10px] font-mono text-text-muted uppercase tracking-wider">
                Active Workspaces ({projects.length})
              </div>
              {projects.length === 0 ? (
                <div className="px-3 py-2 text-xs text-text-muted">No projects found</div>
              ) : (
                projects.map((p) => (
                  <button
                    key={p.id}
                    onClick={() => {
                      onSelectProject(p.id);
                      setIsDropdownOpen(false);
                    }}
                    className={`w-full text-left px-3 py-2 text-xs font-mono flex items-center justify-between hover:bg-white/5 transition ${
                      p.id === selectedProjectId ? 'text-cyan-400 font-bold bg-cyan-500/10' : 'text-text-primary'
                    }`}
                  >
                    <span className="truncate">{p.name}</span>
                    <span className="text-[10px] text-text-muted">{p.stats?.passRate ?? 100}%</span>
                  </button>
                ))
              )}
              <p className="px-3 py-2 mt-1 border-t border-border-subtle text-[10px] text-text-muted leading-relaxed">
                Selection is local to this session. Backend results are global; project-scoped data is not wired yet.
              </p>
            </div>
          )}
        </div>

        {/* Settings Parity Group */}
        <div className="hidden lg:flex items-center gap-3 px-3 py-1.5 rounded-lg bg-bg-base border border-border-subtle text-xs font-mono cursor-pointer hover:border-cyan-500/50 transition group" onClick={() => navigate('/settings')}>
          <div className="flex items-center gap-1.5 border-r border-border-subtle pr-3">
            <Cpu className="w-3.5 h-3.5 text-cyan-400 group-hover:text-cyan-300" />
            <span className="text-text-primary capitalize">{settings?.model || 'ollama'}</span>
            <span className="text-text-muted text-[10px]">(${totalSpentEstimated.toFixed(2)})</span>
          </div>
          <div className="flex items-center gap-1.5 border-r border-border-subtle pr-3">
            <Shield className="w-3.5 h-3.5 text-emerald-400" />
            <span className="text-text-primary capitalize">{settings?.security?.egress_policy?.replace('none font-mono', 'sovereign') || 'sovereign'}</span>
          </div>
          <div className="flex items-center gap-1.5 border-r border-border-subtle pr-3">
            <Zap className="w-3.5 h-3.5 text-amber-400" />
            <span className="text-text-primary capitalize">{settings?.copilot?.autonomy || 'assisted'}</span>
          </div>
          <Settings className="w-3.5 h-3.5 text-text-muted group-hover:text-cyan-400 transition" />
        </div>

        {/* Backend Health Badge */}
        <button
          onClick={handleManualHealthCheck}
          className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border text-xs font-mono transition cursor-pointer ${
            isHealthOnline
              ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400 hover:bg-emerald-500/20'
              : 'bg-rose-500/10 border-rose-500/30 text-rose-400 hover:bg-rose-500/20'
          }`}
          title="Check the connection to the Cherenkov engine"
          data-testid="backend-health-badge"
        >
          <Activity className={`w-3.5 h-3.5 ${isHealthChecking ? 'animate-spin' : ''}`} />
          <span className="font-semibold">{isHealthOnline ? 'Backend Online' : 'Offline'}</span>
          <RefreshCw className={`w-3 h-3 text-text-muted ${isHealthChecking ? 'animate-spin' : ''}`} />
        </button>
      </div>
    </header>
  );
};

export default AppHeader;
