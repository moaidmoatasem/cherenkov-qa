import React, { useEffect, useRef } from 'react';
import { X } from 'lucide-react';
import { useReducedMotion } from '../../lib/useReducedMotion';

interface DrawerProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
}

export function Drawer({ isOpen, onClose, title, children }: DrawerProps) {
  const isReduced = useReducedMotion();
  const drawerRef = useRef<HTMLDivElement>(null);

  // Close on ESC
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  // Focus trap
  useEffect(() => {
    if (isOpen && drawerRef.current) {
      const focusableElements = drawerRef.current.querySelectorAll(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
      );
      if (focusableElements.length > 0) {
        (focusableElements[0] as HTMLElement).focus();
      }
    }
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div 
      className="fixed inset-0 z-50 flex justify-end"
      role="dialog"
      aria-modal="true"
      aria-labelledby="drawer-title"
    >
      {/* Backdrop blur fade */}
      <div 
        className="absolute inset-0 bg-black/40 backdrop-blur-sm transition-opacity duration-300"
        onClick={onClose}
      />
      
      {/* Drawer slide-in panel */}
      <div
        ref={drawerRef}
        className={`w-full max-w-xl bg-bg-base border-l border-border-custom flex flex-col h-full shadow-2xl z-10 relative
          ${isReduced ? '' : 'transition-transform duration-200 ease-out translate-x-0'}`}
        style={{
          transform: isReduced ? 'none' : undefined,
        }}
      >
        <div className="flex items-center justify-between p-6 border-b border-border-custom bg-bg-panel">
          <h2 id="drawer-title" className="text-lg font-bold font-display text-text-primary">
            {title}
          </h2>
          <button 
            onClick={onClose}
            aria-label="Close details"
            className="p-1.5 rounded-lg border border-border-custom bg-white/5 hover:bg-white/10 text-text-muted hover:text-text-primary transition-all cursor-pointer focus:outline-none focus:ring-2 focus:ring-glow-blue/50"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        
        <div className="flex-1 overflow-y-auto p-6">
          {children}
        </div>
      </div>
    </div>
  );
}
