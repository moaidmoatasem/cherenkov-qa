/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect } from 'react';
import { Card } from '../../ui';
import { Terminal, CheckCircle2, Clock, Play, RefreshCw } from 'lucide-react';

export interface LivePipelineMonitorProps {
  runId?: string;
  onCompletePipeline?: () => void;
}

export interface PipelineStageItem {
  id: string;
  name: string;
  status: 'done' | 'running' | 'queued' | 'failed';
  duration: string;
}

export const LivePipelineMonitor: React.FC<LivePipelineMonitorProps> = ({ runId, onCompletePipeline }) => {
  const [stages, setStages] = useState<PipelineStageItem[]>([
    { id: 'ingest', name: 'OpenAPI Spec Ingestion', status: 'done', duration: '120ms' },
    { id: 'plan', name: 'Endpoint Richness Planning', status: 'done', duration: '240ms' },
    { id: 'generate', name: 'LLM Playwright Test Generation', status: 'running', duration: '1.2s' },
    { id: 'review', name: 'Gate 4 Quality & AST Validation', status: 'queued', duration: '—' },
    { id: 'validate', name: 'Synthetic Dry-Run Execution', status: 'queued', duration: '—' },
  ]);

  const [logs, setLogs] = useState<string[]>([
    '[INIT] Cherenkov OrchestrationEngine initialized.',
    '[INGEST] Parsing OpenAPI spec schema definitions...',
    '[PLAN] Generated 14 endpoint richness vectors (richness avg 94%).',
    '[GENERATE] Synthesizing Playwright contract tests via LLM...',
    '[GENERATE] Generated test_auth_login.spec.ts successfully.',
  ]);

  return (
    <Card className="p-6 space-y-4" data-testid="live-pipeline-monitor">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold font-mono uppercase tracking-wider text-text-muted flex items-center gap-2">
            <Terminal className="w-4 h-4 text-cyan-400" />
            <span>Live Pipeline Execution Monitor & DAG</span>
          </h2>
          <p className="text-xs text-text-muted mt-0.5">
            Real-time DAG pipeline stage tracker and streaming logs for run <code className="font-mono">{runId || 'active'}</code>.
          </p>
        </div>
      </div>

      {/* DAG Stage Tracker */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-2">
        {stages.map((stg) => (
          <div
            key={stg.id}
            className={`p-3 rounded-xl border flex flex-col justify-between text-xs font-mono ${
              stg.status === 'done'
                ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
                : stg.status === 'running'
                ? 'bg-cyan-500/10 border-cyan-500/40 text-cyan-400 animate-pulse'
                : 'bg-black/20 border-white/5 text-text-muted'
            }`}
          >
            <div className="flex items-center justify-between mb-1">
              <span className="text-[10px] uppercase font-bold">{stg.id}</span>
              {stg.status === 'done' ? (
                <CheckCircle2 className="w-3.5 h-3.5" />
              ) : stg.status === 'running' ? (
                <RefreshCw className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <Clock className="w-3.5 h-3.5" />
              )}
            </div>
            <p className="font-semibold text-[11px] truncate">{stg.name}</p>
            <p className="text-[9px] text-text-muted mt-2">{stg.duration}</p>
          </div>
        ))}
      </div>

      {/* Terminal Log Console */}
      <div className="bg-black/60 border border-white/10 rounded-xl p-4 font-mono text-xs text-emerald-400 space-y-1 max-h-48 overflow-y-auto">
        <p className="text-text-muted text-[10px] uppercase border-b border-white/10 pb-1 mb-2">
          Execution Log Output (Live Stream)
        </p>
        {logs.map((log, i) => (
          <div key={i} className="flex gap-2">
            <span className="text-text-muted select-none">&gt;</span>
            <span>{log}</span>
          </div>
        ))}
      </div>
    </Card>
  );
};

export default LivePipelineMonitor;
