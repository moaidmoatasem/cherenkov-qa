/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useEffect } from 'react';
import { Keyboard, X } from 'lucide-react';
import { SHORTCUTS } from '../journey/config';

export interface KeyboardMapOverlayProps {
  isOpen: boolean;
  onClose: () => void;
}

/**
 * The "?" help overlay. Lists only shortcuts GlobalShortcuts actually
 * implements (shared SHORTCUTS registry), so it can never advertise a binding
 * that does nothing.
 */
export function KeyboardMapOverlay({ isOpen, onClose }: KeyboardMapOverlayProps) {
  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center px-4 bg-black/60 backdrop-blur-sm"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
      data-testid="keyboard-map-overlay"
      role="dialog"
      aria-modal="true"
      aria-labelledby="keyboard-map-title"
    >
      <div className="w-full max-w-md bg-bg-base border border-border-custom rounded-2xl shadow-2xl overflow-hidden cherenkov-glow">
        <div className="flex items-center justify-between px-5 py-4 border-b border-border-custom bg-bg-panel">
          <h2 id="keyboard-map-title" className="text-sm font-bold font-mono text-text-primary flex items-center gap-2">
            <Keyboard className="w-4 h-4 text-cyan-400" />
            Keyboard Shortcuts
          </h2>
          <button
            onClick={onClose}
            aria-label="Close keyboard shortcuts"
            data-testid="btn-close-keyboard-map"
            className="p-1.5 rounded-lg border border-border-custom bg-white/5 hover:bg-white/10 text-text-muted hover:text-text-primary transition-all cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
        <div className="p-2">
          {SHORTCUTS.map((s) => (
            <div
              key={s.keys}
              className="flex items-center justify-between px-3 py-2.5 rounded-lg hover:bg-white/5 transition"
              data-testid="keyboard-shortcut-row"
            >
              <span className="text-xs text-text-muted">{s.label}</span>
              <kbd className="px-2 py-1 text-[10px] font-bold font-mono text-cyan-400 bg-white/5 border border-border-custom rounded">
                {s.keys}
              </kbd>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default KeyboardMapOverlay;
