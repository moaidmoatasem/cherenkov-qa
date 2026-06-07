import { PlugZap, Loader2 } from 'lucide-react';

interface OfflineOverlayProps {
  /** still running the first probe — show a neutral connecting state, not the alarm */
  checking: boolean;
  /** user asked to retry */
  onRetry: () => void;
  /** timestamp of the last health check */
  lastCheckedAt?: Date | null;
}

/**
 * Full-screen honest state shown when the FastAPI review engine is unreachable.
 *
 * Replaces the previous behaviour where LIVE screens failed silently / the app
 * could white-screen when the backend was down (issue #221). Blocks interaction
 * so a QA user never acts on stale or missing data without knowing the engine
 * is offline.
 */
export default function OfflineOverlay({ checking, onRetry, lastCheckedAt }: OfflineOverlayProps) {
  return (
    <div
      role="alertdialog"
      aria-modal="true"
      aria-label="Backend offline"
      className="fixed inset-0 z-[100] flex items-center justify-center bg-bg-base/80 backdrop-blur-md"
    >
      <div className="max-w-md w-full mx-4 rounded-2xl border border-danger-custom/30 bg-bg-base/95 p-8 text-center space-y-5 shadow-[0_0_40px_rgba(239,68,68,0.12)]">
        <div className="flex justify-center">
          {checking ? (
            <Loader2 className="w-10 h-10 text-glow-blue animate-spin" aria-hidden="true" />
          ) : (
            <PlugZap className="w-10 h-10 text-danger-custom" aria-hidden="true" />
          )}
        </div>
        <h2 className="font-display font-semibold text-lg text-text-primary">
          {checking ? 'Connecting to the Cherenkov engine…' : 'Backend offline'}
        </h2>
        <p className="text-xs text-[#7D8DA1] leading-relaxed">
          {checking
            ? 'Probing the review API on /api/v1/health.'
            : 'The FastAPI review engine is unreachable, so live data cannot load. Start it, then retry:'}
        </p>
        {!checking && (
          <div className="space-y-4">
            <pre className="text-left text-[11px] font-mono bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-text-primary overflow-x-auto">
              python3 cherenkov.py review --port 8000
            </pre>
            {lastCheckedAt && (
              <p className="text-[10px] text-[#7D8DA1] font-mono">
                Last checked at: {lastCheckedAt.toLocaleTimeString()}
              </p>
            )}
          </div>
        )}
        <button
          onClick={onRetry}
          disabled={checking}
          className="px-6 py-2 bg-glow-blue hover:bg-opacity-95 disabled:opacity-50 text-slate-950 font-bold text-xs rounded-xl uppercase font-mono tracking-wider transition cursor-pointer"
        >
          {checking ? 'Checking…' : 'Retry connection'}
        </button>
      </div>
    </div>
  );
}
