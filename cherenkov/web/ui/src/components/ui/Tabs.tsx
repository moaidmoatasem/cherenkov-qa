import React, { useRef } from 'react';

interface TabItem {
  id: string;
  label: string;
  count?: number;
}

interface TabsProps {
  items: TabItem[];
  activeId: string;
  onChange: (id: string) => void;
  className?: string;
}

export function Tabs({ items, activeId, onChange, className = '' }: TabsProps) {
  const tabsRef = useRef<(HTMLButtonElement | null)[]>([]);

  const handleKeyDown = (event: React.KeyboardEvent<HTMLButtonElement>, index: number) => {
    let nextIndex = -1;
    if (event.key === 'ArrowRight') {
      nextIndex = (index + 1) % items.length;
    } else if (event.key === 'ArrowLeft') {
      nextIndex = (index - 1 + items.length) % items.length;
    }

    if (nextIndex !== -1) {
      tabsRef.current[nextIndex]?.focus();
      onChange(items[nextIndex].id);
    }
  };

  return (
    <div
      role="tablist"
      aria-label="Screen Tabs"
      className={`flex items-center gap-1 bg-white/5 border border-border-custom p-1 rounded-xl w-fit ${className}`}
    >
      {items.map((item, index) => {
        const isActive = item.id === activeId;
        return (
          <button
            key={item.id}
            ref={(el) => { tabsRef.current[index] = el; }}
            role="tab"
            aria-selected={isActive}
            aria-controls={`panel-${item.id}`}
            id={`tab-${item.id}`}
            tabIndex={isActive ? 0 : -1}
            onClick={() => onChange(item.id)}
            onKeyDown={(e) => handleKeyDown(e, index)}
            className={`px-4 py-1.5 rounded-lg text-sm font-semibold tracking-wide transition-all cursor-pointer focus:outline-none focus:ring-2 focus:ring-glow-blue/50
              ${isActive
                ? 'bg-glow-blue text-bg-base shadow-[0_0_10px_rgba(34,211,238,0.2)]'
                : 'text-text-muted hover:text-text-primary hover:bg-white/5'
              }`}
          >
            <span className="flex items-center gap-2">
              {item.label}
              {item.count !== undefined && (
                <span className={`px-1.5 py-0.5 text-xs font-mono font-bold rounded-md
                  ${isActive ? 'bg-bg-base/20 text-bg-base' : 'bg-white/10 text-text-primary'}`}>
                  {item.count}
                </span>
              )}
            </span>
          </button>
        );
      })}
    </div>
  );
}
