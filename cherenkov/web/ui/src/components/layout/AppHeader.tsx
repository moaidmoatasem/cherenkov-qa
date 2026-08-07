/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useEffect, useState } from 'react';
import CherenkovLogo from '../CherenkovLogo';
import { Project } from '../../types';
import { fetchProjects, fetchMetricsData, checkBackendHealth, fetchSettings, SystemSettings } from '../../lib/api';
import { ChevronDown, RefreshCw, Cpu, Activity, Shield, Zap, Settings } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

interface AppHeaderProps {
  activeWorkspaceTitle: string;
  activeWorkspaceSubtitle?: string;
  selectedProjectId: string | null;
  onSelectProject: (projectId: string) => void;
  tokenUsagePercent?: number;
  totalSpentEstimated?: number;
  online?: boolean;
}

export const AppHeader: React.FC<AppHeaderProps> = ({
  activeWorkspaceTitle,
  activeWorkspaceSubtitle = 'Autonomous API Conformance & QA Engine',
  selectedProjectId,
  onSelectProject,
  tokenUsagePercent = 0,
  totalSpentEstimated = 0,
  online = true,
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
    <header className="h-16 px-6 border-b border-border-subtle bg-bg-surface/80 backdrop-blur-md flex items-center justify-between z-20 shrink-0 select-none">
      {/* Brand & Active Workspace Context */}
      <div className="flex items-center gap-6">
        <div className="flex items-center gap-3">
          <CherenkovLogo className="w-7 h-7 text-cyan-400" />
          <div className="flex flex-col">
            <span className="font-mono text-sm font-bold tracking-wider text-text-primary flex items-center gap-1.5">
              CHERENKOV <span className="text-cyan-400 text-xs font-semibold px-1.5 py-0.5 rounded bg-cyan-500/10 border border-cyan-500/20">QA</span>
            </span>
          </div>
        </div>

        <div className="h-6 w-px bg-border-subtle" />

        {/* Workspace Title */}
        <div>
          <h1 className="text-sm font-semibold font-mono text-text-primary flex items-center gap-2">
            {activeWorkspaceTitle}
          </h1>
          <p className="text-[11px] text-text-muted">{activeWorkspaceSubtitle}</p>
        </div>
      </div>

      {/* Center/Right Status Controls */}
      <div className="flex items-center gap-4">
        {/* Active Project Dropdown Selector */}
        <div className="relative">
          <button
            onClick={() => setIsDropdownOpen(!isDropdownOpen)}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-bg-base border border-border-subtle hover:border-border-strong text-xs font-mono transition text-text-primary"
            data-testid="project-selector-dropdown"
            title="Workspace selection is cosmetic in this build: it highlights a project here but does not filter backend data, which is global until project-scoped APIs ship."
          >
            <span className="text-text-muted">Project:</span>
            <span className="font-semibold text-cyan-400 max-w-[140px] truncate">
              {currentProject ? currentProject.name : 'Select Project'}
            </span>
            <ChevronDown className="w-3.5 h-3.5 text-text-muted" />
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
          title="Click to probe /api/v1/health"
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
