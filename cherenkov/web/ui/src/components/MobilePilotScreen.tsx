import React, { useState, useEffect } from 'react';
import { Play, Square, RotateCw, CheckCircle, XCircle, Clock, Loader2, AlertTriangle } from 'lucide-react';
import { Card, PageHeader, EmptyState, Skeleton } from './ui';
import { fetchMobilePilotStatus, startMobilePilot, PilotStatus, PilotStep } from '../lib/api';

const STATUS_ICONS: Record<string, React.ReactNode> = {
  passed: <CheckCircle className="w-4 h-4 text-[#3FB950]" />,
  failed: <XCircle className="w-4 h-4 text-[#F85149]" />,
  running: <Loader2 className="w-4 h-4 text-glow-bright animate-spin" />,
  pending: <Clock className="w-4 h-4 text-[#7D8DA1]" />,
  skipped: <AlertTriangle className="w-4 h-4 text-[#D29922]" />,
};

const STATUS_BADGE: Record<string, { label: string; color: string }> = {
  idle: { label: 'Idle', color: 'bg-[#7D8DA1]/20 text-[#7D8DA1] border-[#7D8DA1]/30' },
  running: { label: 'Running', color: 'bg-glow-blue/20 text-glow-bright border-glow-blue/30' },
  done: { label: 'Done', color: 'bg-[#3FB950]/20 text-[#3FB950] border-[#3FB950]/30' },
  failed: { label: 'Failed', color: 'bg-[#F85149]/20 text-[#F85149] border-[#F85149]/30' },
};

export default function MobilePilotScreen() {
  const [pilot, setPilot] = useState<PilotStatus | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isStarting, setIsStarting] = useState(false);

  const poll = async () => {
    try {
      const data = await fetchMobilePilotStatus();
      setPilot(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to poll pilot status');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    poll();
    const id = window.setInterval(poll, 2000);
    return () => window.clearInterval(id);
  }, []);

  const handleStart = async () => {
    setIsStarting(true);
    try {
      await startMobilePilot();
      await poll();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start pilot');
    } finally {
      setIsStarting(false);
    }
  };

  if (error && !pilot) {
    return (
      <div className="p-6 h-full overflow-y-auto space-y-6 grid-bg bg-transparent relative z-10">
        <EmptyState icon={AlertTriangle} title="Pilot Unavailable" description={error} />
      </div>
    );
  }

  const running = pilot?.status === 'running';
  const progress = pilot && pilot.total_steps > 0 ? (pilot.current_step / pilot.total_steps) * 100 : 0;
  const badge = pilot ? STATUS_BADGE[pilot.status] : null;

  return (
    <div className="p-6 h-full overflow-y-auto space-y-6 grid-bg bg-transparent relative z-10" id="mobile-pilot-screen">
      <PageHeader
        title="Mobile Pilot"
        description="Execute and monitor mobile test pilot runs on connected devices."
      />

      <Card className="p-5 space-y-5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <h2 className="text-sm font-semibold text-[#E6EDF3]">Pilot Status</h2>
            {badge && (
              <span data-testid="pilot-status-badge" className={`text-[10px] font-mono px-2 py-0.5 rounded-full border ${badge.color}`}>
                {badge.label}
              </span>
            )}
          </div>
          {pilot?.status === 'idle' && (
            <button
              data-testid="pilot-start-btn"
              onClick={handleStart}
              disabled={isStarting}
              className="flex items-center gap-1.5 px-4 py-2 bg-glow-blue/20 border border-glow-blue/30 rounded-lg text-xs text-glow-bright hover:bg-glow-blue/30 transition cursor-pointer disabled:opacity-50"
            >
              {isStarting ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5" />}
              {isStarting ? 'Starting...' : 'Start Pilot'}
            </button>
          )}
        </div>

        {isLoading ? (
          <div className="space-y-3">
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-3/4" />
            <Skeleton className="h-4 w-1/2" />
          </div>
        ) : pilot ? (
          <>
            {(running || pilot.status === 'done' || pilot.status === 'failed') && (
              <div className="space-y-2">
                <div className="flex justify-between text-xs text-[#7D8DA1]">
                  <span>{pilot.current_step} / {pilot.total_steps} steps</span>
                  <span>{Math.round(progress)}%</span>
                </div>
                <div className="w-full h-2 bg-white/5 rounded-full overflow-hidden">
                  <div
                    data-testid="pilot-progress-bar"
                    className={`h-full rounded-full transition-all duration-500 ${
                      pilot.status === 'failed' ? 'bg-[#F85149]' : 'bg-glow-blue'
                    }`}
                    style={{ width: `${progress}%` }}
                  />
                </div>
              </div>
            )}

            {pilot.steps.length > 0 && (
              <div className="space-y-1 max-h-80 overflow-y-auto">
                {pilot.steps.map((step: PilotStep) => (
                  <div
                    key={step.step_id}
                    data-testid={`pilot-step-${step.step_id}`}
                    className="flex items-start gap-3 p-2.5 rounded-lg bg-white/[0.02] border border-white/5 text-xs"
                  >
                    <div className="mt-0.5 shrink-0">
                      {STATUS_ICONS[step.status] || <Clock className="w-4 h-4 text-[#7D8DA1]" />}
                    </div>
                    <div className="flex-1 min-w-0 space-y-0.5">
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-[#E6EDF3]">{step.action}</span>
                        <span className="text-[#7D8DA1] truncate">{step.target}</span>
                      </div>
                      {step.expected && (
                        <div className="text-[#7D8DA1]">
                          expected: <span className="font-mono">{step.expected}</span>
                        </div>
                      )}
                      {step.actual && (
                        <div className={step.status === 'failed' ? 'text-[#F85149]' : 'text-[#7D8DA1]'}>
                          actual: <span className="font-mono">{step.actual}</span>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}

            {pilot.status === 'done' && (
              <div className="flex items-center gap-2 text-xs text-[#3FB950] pt-1">
                <CheckCircle className="w-4 h-4" />
                Pilot completed successfully
              </div>
            )}
            {pilot.status === 'failed' && (
              <div className="flex items-center gap-2 text-xs text-[#F85149] pt-1">
                <XCircle className="w-4 h-4" />
                Pilot encountered errors
              </div>
            )}
          </>
        ) : null}
      </Card>
    </div>
  );
}
