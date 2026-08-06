/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React from 'react';
import { PlusCircle } from 'lucide-react';
import {
  OTHER_SURFACES,
  SURFACE_CHROME,
  SURFACE_TITLES,
  useNavSurfaces,
} from '../../journey/config';
import type { WorkspaceId } from '../../journey/types';

export type { WorkspaceId };

export interface NavigationBarProps {
  activeWorkspace: WorkspaceId;
  onSelectWorkspace: (workspace: WorkspaceId) => void;
  pendingReviewCount?: number;
  onNewRun?: () => void;
}

export interface WorkspaceNavItem {
  id: WorkspaceId;
  label: string;
  description: string;
  icon: React.ComponentType<{ className?: string }>;
  badge?: number;
}

function navItem(id: WorkspaceId): WorkspaceNavItem {
  return {
    id,
    label: SURFACE_TITLES[id].title,
    description: SURFACE_TITLES[id].subtitle,
    icon: SURFACE_CHROME[id].icon,
  };
}

export const NavigationBar: React.FC<NavigationBarProps> = ({
  activeWorkspace,
  onSelectWorkspace,
  pendingReviewCount = 0,
  onNewRun,
}) => {
  // Order follows the journey the backend runs, so the nav cannot drift from
  // the loop the way a second hardcoded list did.
  const navSurfaces = useNavSurfaces();

  const renderNavItem = (item: WorkspaceNavItem) => {
    const Icon = item.icon;
    const isActive = activeWorkspace === item.id;
    const badgeCount = item.id === 'triage' ? pendingReviewCount : item.badge;

    return (
      <button
        key={item.id}
        onClick={() => onSelectWorkspace(item.id)}
        className={`w-full flex items-start gap-3 p-3 rounded-xl transition-all duration-200 cursor-pointer text-left ${
          isActive
            ? 'bg-cyan-500/15 border border-cyan-500/40 text-cyan-400 shadow-glow-sm'
            : 'border border-transparent text-text-muted hover:text-text-primary hover:bg-white/5'
        }`}
        data-testid={`nav-workspace-${item.id}`}
      >
        <Icon className={`w-5 h-5 shrink-0 mt-0.5 ${isActive ? 'text-cyan-400' : 'text-text-muted'}`} />
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between">
            <span className="font-mono text-xs font-bold tracking-wide">{item.label}</span>
            {badgeCount !== undefined && badgeCount > 0 && (
              <span className="px-1.5 py-0.2 rounded-full text-[10px] font-mono font-bold bg-amber-500/20 text-amber-400 border border-amber-500/30">
                {badgeCount}
              </span>
            )}
          </div>
          <p className="text-[10px] text-text-muted/80 truncate mt-0.5">{item.description}</p>
        </div>
      </button>
    );
  };

  return (
    <nav className="w-64 bg-bg-surface/90 border-r border-border-subtle flex flex-col justify-between p-4 shrink-0 select-none z-10">
      <div className="space-y-6">
        {/* Workspace Quick Actions */}
        {onNewRun && (
          <button
            onClick={onNewRun}
            className="w-full flex items-center justify-center gap-2 py-2.5 px-4 rounded-xl bg-cyan-500/10 border border-cyan-500/30 hover:bg-cyan-500/20 text-cyan-400 font-mono text-xs font-semibold tracking-wide transition-all shadow-glow-sm cursor-pointer"
            data-testid="nav-new-analysis-btn"
          >
            <PlusCircle className="w-4 h-4" />
            <span>New Analysis Run</span>
          </button>
        )}

        {/* The conformance loop, in journey order, plus Settings */}
        <div className="space-y-1">
          <p className="px-3 text-[10px] font-mono uppercase tracking-wider text-text-muted mb-2">
            Workspaces
          </p>
          {navSurfaces.map((id) => renderNavItem(navItem(id)))}
        </div>

        {/* Real, working capability that isn't part of the certified
            spec-conformance loop above -- kept visually distinct rather than
            folded silently into Settings, and deliberately not a peer of the
            loop: an honest, minimal surface, not a claim of parity with a
            dedicated mobile-testing platform. */}
        <div className="space-y-1">
          <p className="px-3 text-[10px] font-mono uppercase tracking-wider text-text-muted mb-2">
            Other Test Surfaces
          </p>
          {OTHER_SURFACES.map((id) => renderNavItem(navItem(id)))}
        </div>
      </div>

      {/* Footer Branding Info */}
      <div className="pt-4 border-t border-border-subtle text-[10px] font-mono text-text-muted flex items-center justify-between">
        <span>Cherenkov QA</span>
        <span className="text-cyan-400 font-semibold">Open Source</span>
      </div>
    </nav>
  );
};

export default NavigationBar;
