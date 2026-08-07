import React, { useEffect, useRef } from 'react';
import { GO_TO_SHORTCUTS } from '../journey/config';
import type { WorkspaceId } from '../journey/types';

interface GlobalShortcutsProps {
  onNewRun: () => void;
  onSearch: () => void;
  onNavigate: (workspace: WorkspaceId) => void;
  onShowHelp: () => void;
}

/**
 * Global keyboard shortcuts. Every binding listed here is also listed in the
 * SHORTCUTS registry that backs the "?" overlay -- the two can never drift.
 * Supports the "g" prefix chord (g d / g a / g t / g m / g s / g b) which
 * jumps straight to a surface, mirroring Vim-style leader navigation.
 */
export default function GlobalShortcuts({ onNewRun, onSearch, onNavigate, onShowHelp }: GlobalShortcutsProps) {
  const gPending = useRef(false);
  const gTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        onSearch();
        return;
      }
      if ((e.metaKey || e.ctrlKey) && e.key === 'n') {
        e.preventDefault();
        onNewRun();
        return;
      }
      // "?" opens the keyboard map. Shift+/ on most layouts.
      if (e.key === '?') {
        e.preventDefault();
        onShowHelp();
        return;
      }
      // "g" prefix chord: g then d/a/t/m/s/b jumps to a surface.
      if (e.key === 'g' && !e.metaKey && !e.ctrlKey && !e.altKey) {
        gPending.current = true;
        if (gTimer.current) clearTimeout(gTimer.current);
        gTimer.current = setTimeout(() => {
          gPending.current = false;
        }, 800);
        return;
      }
      if (gPending.current && !e.metaKey && !e.ctrlKey && !e.altKey) {
        const target = GO_TO_SHORTCUTS[e.key.toLowerCase()];
        if (target) {
          e.preventDefault();
          gPending.current = false;
          if (gTimer.current) clearTimeout(gTimer.current);
          onNavigate(target);
          return;
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      if (gTimer.current) clearTimeout(gTimer.current);
    };
  }, [onNewRun, onSearch, onNavigate, onShowHelp]);

  return null;
}
