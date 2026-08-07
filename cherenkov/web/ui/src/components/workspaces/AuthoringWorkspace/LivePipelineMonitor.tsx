/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useEffect, useState } from 'react';
import { Card } from '../../ui';
import {
  Terminal,
  CheckCircle2,
  Clock,
  RefreshCw,
  XCircle,
  Wifi,
  WifiOff,
  ChevronDown,
  ChevronRight,
  FileCode2,
} from 'lucide-react';
import { useLiveEvents } from '../../../hooks/useLiveEvents';

export interface LivePipelineMonitorProps {
  runId?: string;
  onCompletePipeline?: () => void;
}

type StageStatus = 'done' | 'running' | 'queued' | 'failed' | 'skipped';

interface PipelineStageItem {
  id: string;
  name: string;
  status: StageStatus;
  duration: string;
}

/** Real test_generated payload (orchestrator.py _emit_event). */
interface GeneratedTestEvidence {
  endpoint: string;
  method: string;
  agent: string;
  code: string;
}

// Mirrors the real orchestrator stages (cherenkov/core/orchestrator.py
// _emit_event calls) -- there is no separate live "validate" stage; dry-run
// execution happens as a gate inside REVIEW.
const IDLE_STAGES: PipelineStageItem[] = [
  { id: 'INGEST', name: 'Analysis', status: 'queued', duration: '—' },
  { id: 'PLAN', name: 'Planning', status: 'queued', duration: '—' },
  { id: 'GENERATE', name: 'Design & Generation', status: 'queued', duration: '—' },
  { id: 'REVIEW', name: 'Quality Review', status: 'queued', duration: '—' },
];

export const LivePipelineMonitor: React.FC<LivePipelineMonitorProps> = ({ runId, onCompletePipeline }) => {
  const { lastEvent, connected } = useLiveEvents();
  const [stages, setStages] = useState<PipelineStageItem[]>(IDLE_STAGES);
  const [logs, setLogs] = useState<string[]>([]);
  const [started, setStarted] = useState(false);
  // J1: real evidence captured from test_generated events (method/endpoint/
  // agent/code). No request/response or screenshots are fabricated here --
  // the orchestrator simply does not emit them in this payload.
  const [evidence, setEvidence] = useState<GeneratedTestEvidence[]>([]);
  const [expandedEvidence, setExpandedEvidence] = useState<number | null>(null);

  // A new run started -- drop any stale state from the previous one.
  useEffect(() => {
    if (!runId) return;
    setStages(IDLE_STAGES);
    setLogs([`[RUN] Started ${runId}`]);
    setEvidence([]);
    setExpandedEvidence(null);
    setStarted(true);
  }, [runId]);

  useEffect(() => {
    if (!lastEvent || !started) return;
    const { type, payload } = lastEvent as { type: string; payload: Record<string, any> };

    const setStageStatus = (stageId: string, status: StageStatus, duration?: string) => {
      setStages((prev) =>
        prev.map((s) => (s.id === stageId ? { ...s, status, duration: duration ?? s.duration } : s))
      );
    };

    switch (type) {
      case 'stage_start':
        setStageStatus(payload.stage, 'running');
        setLogs((l) => [...l, `[${payload.stage}] Running...`]);
        break;
      case 'stage_success':
        setStageStatus(payload.stage, 'done', `${payload.duration_ms}ms`);
        setLogs((l) => [...l, `[${payload.stage}] ${payload.summary}`]);
        break;
      case 'stage_skip':
        setStageStatus(payload.stage, 'skipped');
        setLogs((l) => [...l, `[${payload.stage}] Skipped: ${payload.reason}`]);
        break;
      case 'test_generated':
        setLogs((l) => [...l, `[GENERATE] ${payload.method} ${payload.endpoint} -> test written`]);
        setEvidence((prev) => [
          ...prev,
          {
            endpoint: payload.endpoint,
            method: payload.method,
            agent: payload.agent,
            code: payload.code,
          },
        ]);
        break;
      case 'replan_trigger':
        setLogs((l) => [...l, `[PLAN] Re-planning ${payload.endpoint} (${payload.case_type}) after a dry-run failure`]);
        break;
      case 'pipeline_error':
        setLogs((l) => [...l, `[ERROR] ${payload.detail}`]);
        setStages((prev) => prev.map((s) => (s.status === 'running' ? { ...s, status: 'failed' } : s)));
        break;
      case 'pipeline_complete':
        setLogs((l) => [
          ...l,
          payload.success
            ? `[DONE] ${payload.scenarios_passed}/${payload.scenarios_total} scenarios passed (${payload.total_duration_ms}ms)`
            : `[DONE] Pipeline stopped: ${payload.reason || 'see errors above'}`,
        ]);
        if (onCompletePipeline) onCompletePipeline();
        break;
      default:
        break;
    }
  }, [lastEvent, started, onCompletePipeline]);

  return (
    <Card className="p-6 space-y-4" data-testid="live-pipeline-monitor">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold font-mono uppercase tracking-wider text-text-muted flex items-center gap-2">
            <Terminal className="w-4 h-4 text-cyan-400" />
            <span>Live Pipeline Monitor</span>
          </h2>
          <p className="text-xs text-text-muted mt-0.5">
            {started
              ? `Real-time stage tracker for run `
              : 'Run a generation above to see live analysis -> planning -> design -> review progress here.'}
            {started && <code className="font-mono">{runId}</code>}
          </p>
        </div>
        <div
          className={`flex items-center gap-1.5 text-[10px] font-mono ${connected ? 'text-emerald-400' : 'text-text-muted'}`}
          title={connected ? 'Live event stream connected' : 'Live event stream disconnected'}
        >
          {connected ? <Wifi className="w-3.5 h-3.5" /> : <WifiOff className="w-3.5 h-3.5" />}
          {connected ? 'Live' : 'Offline'}
        </div>
      </div>

      {/* Stage Tracker */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-2">
        {stages.map((stg) => (
          <div
            key={stg.id}
            className={`p-3 rounded-xl border flex flex-col justify-between text-xs font-mono ${
              stg.status === 'done'
                ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
                : stg.status === 'running'
                ? 'bg-cyan-500/10 border-cyan-500/40 text-cyan-400 animate-pulse'
                : stg.status === 'failed'
                ? 'bg-rose-500/10 border-rose-500/30 text-rose-400'
                : stg.status === 'skipped'
                ? 'bg-amber-500/10 border-amber-500/30 text-amber-400'
                : 'bg-black/20 border-white/5 text-text-muted'
            }`}
          >
            <div className="flex items-center justify-between mb-1">
              <span className="text-[10px] uppercase font-bold">{stg.id}</span>
              {stg.status === 'done' ? (
                <CheckCircle2 className="w-3.5 h-3.5" />
              ) : stg.status === 'running' ? (
                <RefreshCw className="w-3.5 h-3.5 animate-spin" />
              ) : stg.status === 'failed' ? (
                <XCircle className="w-3.5 h-3.5" />
              ) : (
                <Clock className="w-3.5 h-3.5" />
              )}
            </div>
            <p className="font-semibold text-[11px] truncate">{stg.name}</p>
            <p className="text-[9px] text-text-muted mt-2">{stg.duration}</p>
          </div>
        ))}
      </div>

      {/* J1: Live Preview -- skeleton rows during the planning phase, before
          the generated tests land. Rendered only while a stage is running so
          the placeholders never outlive the work they stand for. */}
      {stages.some((s) => s.status === 'running') && (
        <div className="space-y-2" data-testid="live-preview-skeletons">
          <p className="text-[10px] font-mono uppercase tracking-wider text-text-muted">
            Live Preview — planning generated tests
          </p>
          {[0, 1, 2].map((i) => (
            <div
              key={i}
              className="flex items-center gap-3 p-3 rounded-xl border border-white/5 bg-black/20 animate-pulse"
            >
              <div className="w-16 h-3 rounded bg-white/10" />
              <div className="flex-1 h-3 rounded bg-white/10" />
              <div className="w-24 h-3 rounded bg-white/10" />
            </div>
          ))}
        </div>
      )}

      {/* J1: Evidence Disclosure -- inline request/response-grade evidence from
          the real test_generated payload (method, endpoint, generating agent,
          generated code). Screenshots are not fabricated when absent. */}
      {evidence.length > 0 && (
        <div className="space-y-2" data-testid="pipeline-evidence">
          <p className="text-[10px] font-mono uppercase tracking-wider text-text-muted">
            Evidence — generated tests ({evidence.length})
          </p>
          {evidence.map((ev, idx) => {
            const isExpanded = expandedEvidence === idx;
            return (
              <div key={idx} className="rounded-xl border border-white/10 bg-black/30 overflow-hidden">
                <button
                  onClick={() => setExpandedEvidence(isExpanded ? null : idx)}
                  className="w-full flex items-center gap-2 px-3 py-2 text-left hover:bg-white/5 transition"
                  data-testid={`evidence-row-${idx}`}
                  aria-expanded={isExpanded}
                >
                  {isExpanded ? (
                    <ChevronDown className="w-3.5 h-3.5 text-cyan-400" />
                  ) : (
                    <ChevronRight className="w-3.5 h-3.5 text-text-muted" />
                  )}
                  <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-cyan-500/15 text-cyan-400 border border-cyan-500/30">
                    {ev.method}
                  </span>
                  <span className="text-xs font-mono text-text-primary truncate">{ev.endpoint}</span>
                  <span className="ml-auto text-[10px] font-mono text-text-muted hidden sm:inline">
                    {ev.agent}
                  </span>
                </button>
                {isExpanded && (
                  <pre className="px-3 pb-3 text-[10px] font-mono text-emerald-300/90 overflow-x-auto max-h-64">
                    {ev.code || '// generated code not provided in event payload'}
                  </pre>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Terminal Log Console */}
      <div className="bg-black/60 border border-white/10 rounded-xl p-4 font-mono text-xs text-emerald-400 space-y-1 max-h-48 overflow-y-auto">
        <p className="text-text-muted text-[10px] uppercase border-b border-white/10 pb-1 mb-2">
          Live Event Log
        </p>
        {logs.length === 0 ? (
          <p className="text-text-muted">No activity yet.</p>
        ) : (
          logs.map((log, i) => (
            <div key={i} className="flex gap-2">
              <span className="text-text-muted select-none">&gt;</span>
              <span>{log}</span>
            </div>
          ))
        )}
      </div>
    </Card>
  );
};

export default LivePipelineMonitor;
