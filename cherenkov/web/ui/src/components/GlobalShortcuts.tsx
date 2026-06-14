import React, { useEffect } from 'react';

interface GlobalShortcutsProps {
  onNewRun: () => void;
  onSearch: () => void;
}

export default function GlobalShortcuts({ onNewRun, onSearch }: GlobalShortcutsProps) {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        onSearch();
      }
      if ((e.metaKey || e.ctrlKey) && e.key === 'n') {
        e.preventDefault();
        onNewRun();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onNewRun, onSearch]);

  return null;
}
