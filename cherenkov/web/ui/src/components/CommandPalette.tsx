import React, { useState, useEffect, useRef } from 'react';
import { Search, Terminal, Compass, Zap, FolderGit2, X } from 'lucide-react';
import { Project } from '../types';

interface CommandPaletteProps {
  onNavigate: (tabId: string) => void;
  onNewRun: () => void;
  projects: Project[];
  onSelectProject: (id: string) => void;
}

interface PaletteItem {
  id: string;
  title: string;
  subtitle: string;
  category: 'NAVIGATION' | 'ACTIONS' | 'WORKSPACES';
  icon: React.ComponentType<any>;
  action: () => void;
}

export default function CommandPalette({
  onNavigate,
  onNewRun,
  projects,
  onSelectProject
}: CommandPaletteProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [search, setSearch] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Toggle on Cmd+K or Ctrl+K
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setIsOpen((prev) => !prev);
      }
      if (e.key === 'Escape' && isOpen) {
        setIsOpen(false);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen]);

  // Focus input when opened
  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 50);
      setSearch('');
      setSelectedIndex(0);
    }
  }, [isOpen]);

  // Command registry
  const items: PaletteItem[] = [
    // NAVIGATION
    { id: 'overview', title: 'Go to Overview', subtitle: 'View release readiness score & learnings', category: 'NAVIGATION', icon: Compass, action: () => onNavigate('overview') },
    { id: 'truth-map', title: 'Go to Truth Map', subtitle: 'View spec-to-traffic claims graph', category: 'NAVIGATION', icon: Compass, action: () => onNavigate('truth-map') },
    { id: 'divergences', title: 'Go to Divergences', subtitle: 'Triage active system deviations', category: 'NAVIGATION', icon: Zap, action: () => onNavigate('divergences') },
    { id: 'explore', title: 'Go to Explore Screen', subtitle: 'Autonomous second pair of eyes explorer', category: 'NAVIGATION', icon: Search, action: () => onNavigate('explore') },
    { id: 'author', title: 'Go to Author by Intent', subtitle: 'Interactive plain-English QA Copilot', category: 'NAVIGATION', icon: Terminal, action: () => onNavigate('author') },
    { id: 'review', title: 'Go to Review Queue', subtitle: 'Approve or edit generated tests', category: 'NAVIGATION', icon: Compass, action: () => onNavigate('review') },
    { id: 'signals', title: 'Go to Signals', subtitle: 'Performance, Visual, and Coverage logs', category: 'NAVIGATION', icon: Compass, action: () => onNavigate('signals') },
    { id: 'healing', title: 'Go to Healing', subtitle: 'API drift repair suggestions', category: 'NAVIGATION', icon: Compass, action: () => onNavigate('healing') },
    { id: 'eject', title: 'Go to Eject Suite', icon: Compass, subtitle: 'Export standalone Playwright tests', category: 'NAVIGATION', action: () => onNavigate('eject') },
    { id: 'governance', title: 'Go to Governance', subtitle: 'Certification audit and traceability', category: 'NAVIGATION', icon: Compass, action: () => onNavigate('governance') },
    { id: 'memory', title: 'Go to Memory & Pairing', subtitle: 'Reflector senior team idioms', category: 'NAVIGATION', icon: Compass, action: () => onNavigate('memory') },

    // ACTIONS
    { id: 'action-new-run', title: 'New Run Setup', subtitle: 'Launch spec parser setup wizard', category: 'ACTIONS', icon: Terminal, action: () => { onNewRun(); } },
    { id: 'action-author-test', title: 'Author a test...', subtitle: 'Type plain intent to generate Playwright test', category: 'ACTIONS', icon: Terminal, action: () => { onNavigate('author'); } },
    { id: 'action-open-divergences', title: 'Open Divergences list', subtitle: 'Inspect active drifts and errors', category: 'ACTIONS', icon: Zap, action: () => { onNavigate('divergences'); } },

    // WORKSPACES
    ...projects.map((p) => ({
      id: `project-${p.id}`,
      title: `Switch Workspace: ${p.name}`,
      subtitle: `Load test runs for ${p.id}`,
      category: 'WORKSPACES' as const,
      icon: FolderGit2,
      action: () => { onSelectProject(p.id); }
    }))
  ];

  // Filtering
  const filtered = items.filter((item) =>
    item.title.toLowerCase().includes(search.toLowerCase()) ||
    item.subtitle.toLowerCase().includes(search.toLowerCase()) ||
    item.category.toLowerCase().includes(search.toLowerCase())
  );

  // List Keyboard Controls
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex((prev) => (prev + 1) % filtered.length);
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex((prev) => (prev - 1 + filtered.length) % filtered.length);
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (filtered[selectedIndex]) {
        filtered[selectedIndex].action();
        setIsOpen(false);
      }
    }
  };

  // Close when clicking outside dialog container
  const handleBackdropClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) {
      setIsOpen(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center pt-[10vh] px-4 bg-black/60 backdrop-blur-sm"
      onClick={handleBackdropClick}
    >
      <div
        ref={containerRef}
        className="w-full max-w-2xl bg-bg-base border border-border-custom rounded-2xl shadow-2xl flex flex-col max-h-[70vh] overflow-hidden cherenkov-glow"
        onKeyDown={handleKeyDown}
      >
        {/* Search header */}
        <div className="flex items-center gap-3 px-4 border-b border-border-custom bg-bg-panel py-3.5">
          <Search className="w-5 h-5 text-glow-blue shrink-0" />
          <input
            ref={inputRef}
            id="command-palette-input"
            name="command-palette"
            type="text"
            placeholder="Type page name or action command (e.g. 'author', 'setup', 'divergences')..."
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setSelectedIndex(0);
            }}
            className="w-full bg-transparent text-sm text-text-primary focus:outline-none placeholder-text-muted"
          />
          <div className="flex items-center gap-1.5 shrink-0">
            <kbd className="hidden sm:inline-block px-1.5 py-0.5 text-[10px] font-bold font-mono text-text-muted bg-white/5 border border-border-custom rounded">ESC</kbd>
            <button onClick={() => setIsOpen(false)} className="text-text-muted hover:text-text-primary p-0.5 rounded cursor-pointer">
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Search Results list */}
        <div className="flex-1 overflow-y-auto p-2 space-y-1 select-none">
          {filtered.length === 0 ? (
            <div className="p-4 text-center text-sm text-text-muted">
              No matching actions or navigation targets found.
            </div>
          ) : (
            filtered.map((item, index) => {
              const Icon = item.icon;
              const isSelected = index === selectedIndex;
              return (
                <div
                  key={item.id}
                  onClick={() => {
                    item.action();
                    setIsOpen(false);
                  }}
                  className={`px-4 py-3 rounded-xl flex items-center justify-between gap-3 cursor-pointer transition-all duration-150
                    ${isSelected
                      ? 'bg-white/10 text-text-primary'
                      : 'text-text-muted hover:text-text-primary hover:bg-white/5'
                    }`}
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <div className={`p-1.5 rounded-lg border border-border-custom bg-white/5 shrink-0 ${isSelected ? 'text-glow-bright border-glow-blue/20' : 'text-text-muted'}`}>
                      <Icon className="w-4 h-4" />
                    </div>
                    <div className="min-w-0">
                      <span className={`block text-sm font-semibold truncate ${isSelected ? 'text-glow-bright' : 'text-text-primary'}`}>
                        {item.title}
                      </span>
                      <span className="block text-xs text-text-muted mt-0.5 truncate">
                        {item.subtitle}
                      </span>
                    </div>
                  </div>
                  <span className={`text-[10px] font-bold font-mono tracking-wider px-2 py-0.5 rounded bg-white/5 border border-border-custom uppercase shrink-0
                    ${isSelected ? 'text-glow-bright border-glow-blue/15' : 'text-text-muted'}`}>
                    {item.category}
                  </span>
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}
