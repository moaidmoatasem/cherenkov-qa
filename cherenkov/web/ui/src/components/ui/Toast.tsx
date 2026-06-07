import React, { createContext, useContext, useState, useCallback, useEffect, useRef } from 'react';
import { X, CheckCircle2, AlertTriangle, AlertCircle, Info } from 'lucide-react';
import { useReducedMotion } from '../../lib/useReducedMotion';

export type ToastType = 'success' | 'warning' | 'danger' | 'error' | 'info';

export interface ToastItem {
  id: string;
  message: string;
  type: ToastType;
  actionLabel?: string;
  onAction?: () => void;
}

interface ToastContextType {
  toast: (message: string, type?: ToastType, options?: { actionLabel?: string; onAction?: () => void }) => void;
  toasts: ToastItem[];
  dismiss: (id: string) => void;
}

const ToastContext = createContext<ToastContextType | undefined>(undefined);

export function useToast() {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error('useToast must be used within a ToastProvider');
  }
  return context;
}

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const dismiss = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const toast = useCallback((
    message: string, 
    type: ToastType = 'info', 
    options?: { actionLabel?: string; onAction?: () => void }
  ) => {
    const id = Math.random().toString(36).substring(2, 9);
    setToasts((prev) => {
      const next = [...prev, { id, message, type, ...options }];
      // Keep max 3 stacked
      if (next.length > 3) {
        return next.slice(next.length - 3);
      }
      return next;
    });
  }, []);

  return (
    <ToastContext.Provider value={{ toast, toasts, dismiss }}>
      {children}
      <ToastContainer toasts={toasts} dismiss={dismiss} />
    </ToastContext.Provider>
  );
}

function ToastContainer({ toasts, dismiss }: { toasts: ToastItem[]; dismiss: (id: string) => void }) {
  return (
    <div 
      className="fixed bottom-6 right-6 flex flex-col gap-3 z-50 pointer-events-none max-w-sm w-full"
      role="status"
      aria-live="assertive"
    >
      {toasts.map((item) => (
        <ToastComponent key={item.id} item={item} dismiss={dismiss} />
      ))}
    </div>
  );
}

function ToastComponent({ item, dismiss }: { item: ToastItem; dismiss: (id: string) => void; key?: string }) {
  const isReduced = useReducedMotion();
  const [isHovered, setIsHovered] = useState(false);
  const timerRef = useRef<number | null>(null);

  const startTimer = useCallback(() => {
    timerRef.current = window.setTimeout(() => {
      dismiss(item.id);
    }, 4000);
  }, [item.id, dismiss]);

  const clearTimer = useCallback(() => {
    if (timerRef.current) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  useEffect(() => {
    if (!isHovered) {
      startTimer();
    } else {
      clearTimer();
    }
    return clearTimer;
  }, [isHovered, startTimer, clearTimer]);

  const icons: Record<ToastType, React.ReactNode> = {
    success: <CheckCircle2 className="w-5 h-5 text-success-custom" />,
    warning: <AlertTriangle className="w-5 h-5 text-warning-custom" />,
    danger: <AlertCircle className="w-5 h-5 text-danger-custom" />,
    error: <AlertCircle className="w-5 h-5 text-danger-custom" />,
    info: <Info className="w-5 h-5 text-glow-blue" />,
  };

  const borders: Record<ToastType, string> = {
    success: 'border-success-custom/30 shadow-[0_0_10px_rgba(16,185,129,0.1)]',
    warning: 'border-warning-custom/30 shadow-[0_0_10px_rgba(245,158,11,0.1)]',
    danger: 'border-danger-custom/30 shadow-[0_0_10px_rgba(239,68,68,0.1)]',
    error: 'border-danger-custom/30 shadow-[0_0_10px_rgba(239,68,68,0.1)]',
    info: 'border-glow-blue/30 shadow-[0_0_10px_rgba(34,211,238,0.1)]',
  };

  return (
    <div
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      className={`pointer-events-auto border bg-bg-base/95 backdrop-blur px-4 py-3 rounded-xl flex items-start gap-3 shadow-lg 
        ${borders[item.type]} 
        ${isReduced ? '' : 'transition-all duration-300 transform scale-100'}`}
    >
      <div className="mt-0.5">{icons[item.type]}</div>
      
      <div className="flex-1 flex flex-col gap-1.5 min-w-0">
        <p className="text-sm font-medium text-text-primary break-words">
          {item.message}
        </p>
        {item.onAction && item.actionLabel && (
          <button
            onClick={() => {
              item.onAction?.();
              dismiss(item.id);
            }}
            className="text-xs font-bold text-glow-blue hover:text-glow-bright tracking-wider text-left uppercase transition-colors cursor-pointer"
          >
            {item.actionLabel}
          </button>
        )}
      </div>

      <button
        onClick={() => dismiss(item.id)}
        aria-label="Dismiss notification"
        className="text-text-muted hover:text-text-primary p-0.5 rounded transition-all cursor-pointer focus:outline-none focus:ring-1 focus:ring-glow-blue/50"
      >
        <X className="w-4 h-4" />
      </button>
    </div>
  );
}
