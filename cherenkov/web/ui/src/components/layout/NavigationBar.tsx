/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useEffect, useState } from 'react';
import { PlusCircle, Pin, PinOff, ChevronDown, ChevronRight } from 'lucide-react';
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
  /** Drawer state below the lg breakpoint. Ignored at desktop widths. */
  mobileOpen?: boolean;
  onCloseMobile?: () => void;
}

export interface WorkspaceNavItem {
  id: WorkspaceId;
  label: string;
  description: string;
  icon: React.ComponentType<{ className?: string }>;
  badge?: number;
}

const PIN_KEY = '[cherenkov] nav_pinned';
const COLLAPSE_KEY = '[cherenkov] nav_collapsed';

function readPinned(): WorkspaceId[] {
  try {
    const raw = JSON.parse(localStorage.getItem(PIN_KEY) || '[]');
    return Array.isArray(raw) ? (raw as WorkspaceId[]) : [];
  } catch {
    return [];
  }
}

function readCollapsed(): Record<string, boolean> {
  try {
    return JSON.parse(localStorage.getItem(COLLAPSE_KEY) || '{}');
  } catch {
    return {};
  }
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
  mobileOpen = false,
  onCloseMobile,
}) => {
  // Order follows the journey the backend runs, so the nav cannot drift from
  // the loop the way a second hardcoded list did.
  const navSurfaces = useNavSurfaces();

  const [pinned, setPinned] = useState<WorkspaceId[]>(readPinned);
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>(() => {
    // The loop used to default collapsed on narrow viewports, back when the
    // sidebar was always on screen and competing for width. Below lg it is now
    // an off-canvas drawer that the user opens deliberately, so opening it to
    // a collapsed list hides the only navigation there is.
    return readCollapsed();
  });

  useEffect(() => {
    localStorage.setItem(PIN_KEY, JSON.stringify(pinned));
  }, [pinned]);

  useEffect(() => {
    localStorage.setItem(COLLAPSE_KEY, JSON.stringify(collapsed));
  }, [collapsed]);

  const togglePin = (id: WorkspaceId) => {
    setPinned((prev) =>
      prev.includes(id) ? prev.filter((p) => p !== id) : [...prev, id]
    );
  };

  const toggleCollapse = (key: string) => {
    setCollapsed((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const renderNavItem = (item: WorkspaceNavItem, opts: { pinned?: boolean } = {}) => {
    const Icon = item.icon;
    const isActive = activeWorkspace === item.id;
    const badgeCount = item.id === 'triage' ? pendingReviewCount : item.badge;

    return (
      <div key={item.id} className="group relative">
        <button
          onClick={() => {
            onSelectWorkspace(item.id);
            onCloseMobile?.();
          }}
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

        {/* Pin toggle -- N-5. Visible on hover, always reachable via keyboard. */}
        <button
          onClick={() => togglePin(item.id)}
          title={opts.pinned ? 'Unpin from sidebar' : 'Pin to sidebar'}
          aria-label={opts.pinned ? `Unpin ${item.label}` : `Pin ${item.label}`}
          data-testid={opts.pinned ? `nav-unpin-${item.id}` : `nav-pin-${item.id}`}
          className={`absolute right-1.5 top-1.5 p-1 rounded-md transition-opacity cursor-pointer ${
            opts.pinned
              ? 'text-cyan-400 opacity-100 hover:bg-cyan-500/15'
              : 'text-text-muted opacity-0 group-hover:opacity-100 focus:opacity-100 hover:bg-white/10'
          }`}
        >
          {opts.pinned ? <PinOff className="w-3.5 h-3.5" /> : <Pin className="w-3.5 h-3.5" />}
        </button>
      </div>
    );
  };

  const renderSection = (
    key: string,
    title: string,
    items: WorkspaceNavItem[],
    collapsible: boolean,
    pinSection: boolean
  ) => {
    const isCollapsed = collapsed[key] ?? false;
    return (
      <div className="space-y-1" data-testid={`nav-section-${key}`}>
        <div className="flex items-center justify-between px-3 mb-2">
          <p className="text-[10px] font-mono uppercase tracking-wider text-text-muted">{title}</p>
          {collapsible && (
            <button
              onClick={() => toggleCollapse(key)}
              aria-expanded={!isCollapsed}
              aria-label={`${isCollapsed ? 'Expand' : 'Collapse'} ${title}`}
              data-testid={`nav-toggle-${key}`}
              className="text-text-muted hover:text-text-primary p-0.5 rounded transition cursor-pointer"
            >
              {isCollapsed ? <ChevronRight className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
            </button>
          )}
        </div>
        {!isCollapsed && (
          <div className="space-y-1">
            {items.map((item) => renderNavItem(item, { pinned: pinSection }))}
          </div>
        )}
      </div>
    );
  };

  const allSurfaces = [...navSurfaces, ...OTHER_SURFACES];
  const pinnedItems = allSurfaces.filter((id) => pinned.includes(id)).map(navItem);
  const loopItems = navSurfaces.filter((id) => !pinned.includes(id)).map(navItem);
  const otherItems = OTHER_SURFACES.filter((id) => !pinned.includes(id)).map(navItem);

  return (
    // Below lg the sidebar becomes an off-canvas drawer. It used to keep its
    // fixed 16rem at every width, so at 375px it left ~120px of content and
    // headings wrapped one word per line.
    <nav
      id="primary-navigation"
      data-mobile-open={mobileOpen ? 'true' : 'false'}
      className={`w-64 bg-bg-surface/90 max-lg:bg-bg-base max-lg:overflow-y-auto border-r border-border-subtle flex flex-col justify-between p-4 shrink-0 select-none z-40
        max-lg:fixed max-lg:inset-y-0 max-lg:left-0 max-lg:shadow-2xl max-lg:transition-transform max-lg:duration-200 max-lg:motion-reduce:transition-none
        ${mobileOpen ? 'max-lg:translate-x-0' : 'max-lg:-translate-x-full'}`}
    >
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

        {/* Pinned workspace shortcuts -- N-5 */}
        {pinnedItems.length > 0 && (
          <div className="space-y-1" data-testid="nav-section-pinned">
            <p className="px-3 text-[10px] font-mono uppercase tracking-wider text-text-muted mb-2">
              Pinned
            </p>
            {pinnedItems.map((item) => renderNavItem(item, { pinned: true }))}
          </div>
        )}

        {/* The conformance loop, in journey order, plus Settings */}
        {renderSection('workspaces', 'Workspaces', loopItems, true, false)}

        {/* Other Test Surfaces */}
        {renderSection('other', 'Other Test Surfaces', otherItems, true, false)}
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
