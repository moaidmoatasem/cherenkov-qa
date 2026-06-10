import React, { useEffect, useState } from 'react';
import { PageHeader, Card, Skeleton, EmptyState, KpiRing, Panel } from './ui';
import { fetchSddStatus, fetchSddSessions, querySddExperience, fetchSddTokens, fetchSddPatterns } from '../lib/api';
import type { SddStatusResponse, SddSessionSummary, SddExperience, SddTokenData, PatternInsight } from '../types';

export default function SddDashboardScreen() {
  const [status, setStatus] = useState<SddStatusResponse | null>(null);
  const [sessions, setSessions] = useState<SddSessionSummary[]>([]);
  const [experiences, setExperiences] = useState<SddExperience[]>([]);
  const [tokens, setTokens] = useState<SddTokenData | null>(null);
  const [patterns, setPatterns] = useState<PatternInsight[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      fetchSddStatus(),
      fetchSddSessions(10),
      querySddExperience(undefined, undefined, 'date', 5),
      fetchSddTokens(),
      fetchSddPatterns(),
    ]).then(([s, sess, exp, tok, pat]) => {
      setStatus(s);
      setSessions(sess);
      setExperiences(exp);
      setTokens(tok);
      setPatterns(pat);
    }).catch(() => {}).finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="p-6 space-y-4">
        <Skeleton variant="rect" className="!w-[300px] !h-8" />
        <div className="grid grid-cols-4 gap-4">
          {[1,2,3,4].map(i => <div key={i}><Skeleton variant="rect" className="!h-30" /></div>)}
        </div>
        <Skeleton variant="rect" className="!h-48" />
      </div>
    );
  }

  const tok = tokens?.current_session;
  const budget = tokens?.budget as Record<string, unknown> | undefined;
  const perSessionBudget = (budget?.per_session as number) || 50000;
  const pct = tok?.total ? Math.round((tok.total / perSessionBudget) * 100) : 0;
  const tokenGlowColor: 'danger' | 'warning' | 'success' = pct > 80 ? 'danger' : pct > 60 ? 'warning' : 'success';

  return (
    <div className="p-6 space-y-6 overflow-y-auto h-full">
      <PageHeader
        title="Agent Cockpit"
        description="SDD sync state, token budget, experience compounding, and agent activity"
      />

      {/* KPI Row */}
      <div className="grid grid-cols-4 gap-4">
        <Card className="p-4 flex flex-col items-center justify-center">
          <KpiRing value={pct} title="Token Budget" size={80} strokeWidth={6}
            glowColor={tokenGlowColor} />
        </Card>
        <Card className="p-4 flex flex-col items-center justify-center">
          <span className="text-3xl font-bold font-mono text-glow-blue">
            {status?.historical?.sessions_completed ?? 0}
          </span>
          <span className="text-xs text-text-muted mt-1">Sessions</span>
          <span className="text-[10px] text-text-muted">
            {status?.historical?.total_all_time ?? 0} total tokens
          </span>
        </Card>
        <Card className="p-4 flex flex-col items-center justify-center">
          <span className="text-3xl font-bold font-mono text-[#10b981]">
            {status?.experience_count ?? 0}
          </span>
          <span className="text-xs text-text-muted mt-1">Experience Records</span>
          <span className="text-[10px] text-text-muted">
            avg {(status?.historical?.avg_per_session ?? 0).toFixed(0)} tok/session
          </span>
        </Card>
        <Card className="p-4 flex flex-col items-center justify-center">
          <span className="text-3xl font-bold font-mono text-[#f59e0b]">
            {status?.session?.status === 'open' ? 'LIVE' : 'IDLE'}
          </span>
          <span className="text-xs text-text-muted mt-1">Session State</span>
          <span className="text-[10px] text-text-muted">
            {(status?.session?.task as string) || 'no active task'}
          </span>
        </Card>
      </div>

      {/* Warning Banner */}
      {pct > 80 && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-xl px-4 py-3 text-sm text-red-400">
          Token budget at {pct}% — compaction recommended.
        </div>
      )}

      <div className="grid grid-cols-2 gap-6">
        {/* Recent Sessions */}
        <Panel className="p-4">
          <h3 className="font-display font-semibold text-sm text-text-primary mb-3">Recent Sessions</h3>
          {sessions.length === 0 ? (
            <EmptyState title="No sessions" description="Run agent_sync before to start" />
          ) : (
            <div className="space-y-2 max-h-64 overflow-y-auto">
              {sessions.map(s => (
                <div key={s.id} className="flex items-center justify-between p-2 rounded-lg bg-white/5 border border-white/10 text-xs">
                  <div className="flex-1 min-w-0">
                    <div className="font-medium text-text-primary truncate">{s.task || 'untitled'}</div>
                    <div className="text-text-muted">{s.id.slice(0, 20)}</div>
                  </div>
                  <div className="text-right flex-shrink-0 ml-2">
                    <div className="font-mono text-glow-blue">{s.token_total}t</div>
                    <div className="text-text-muted">{s.summary?.slice(0, 30) || '—'}</div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </Panel>

        {/* Token Breakdown */}
        <Panel className="p-4">
          <h3 className="font-display font-semibold text-sm text-text-primary mb-3">Current Session Tokens</h3>
          {tok?.session_id ? (
            <div className="space-y-2">
              {(['prompt', 'generate', 'read', 'search'] as const).map(action => {
                const val = tok[action] || 0;
                const pctAction = tok.total ? Math.round((val / tok.total) * 100) : 0;
                return (
                  <div key={action}>
                    <div className="flex justify-between text-xs mb-1">
                      <span className="capitalize text-text-muted">{action}</span>
                      <span className="font-mono text-text-primary">{val.toLocaleString()} ({pctAction}%)</span>
                    </div>
                    <div className="h-1.5 bg-white/10 rounded-full overflow-hidden">
                      <div className="h-full bg-glow-blue rounded-full transition-all" style={{ width: `${pctAction}%` }} />
                    </div>
                  </div>
                );
              })}
              <div className="pt-2 border-t border-white/10 flex justify-between text-xs font-bold">
                <span className="text-text-muted">Total</span>
                <span className="font-mono text-text-primary">{tok.total.toLocaleString()}</span>
              </div>
            </div>
          ) : (
            <EmptyState title="No active session" description="Open a session to track tokens" />
          )}
        </Panel>
      </div>

      {/* Experience + Patterns Row */}
      <div className="grid grid-cols-2 gap-6">
        <Panel className="p-4">
          <h3 className="font-display font-semibold text-sm text-text-primary mb-3">Recent Experience</h3>
          {experiences.length === 0 ? (
            <EmptyState title="No experience yet" description="Log decisions during agent sessions" />
          ) : (
            <div className="space-y-2 max-h-48 overflow-y-auto">
              {experiences.map(e => (
                <div key={e.id} className="p-2 rounded-lg bg-white/5 border border-white/10 text-xs">
                  <div className="flex items-center gap-2 mb-1">
                    <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${
                      e.outcome === 'success' ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'
                    }`}>{e.outcome}</span>
                    <span className="font-mono text-text-muted">{e.token_cost}t</span>
                  </div>
                  <div className="text-text-primary truncate">{e.action}</div>
                  {e.patterns.length > 0 && (
                    <div className="flex gap-1 mt-1 flex-wrap">
                      {e.patterns.map(p => (
                        <span key={p} className="px-1 py-0.5 rounded bg-cyan-500/10 text-[10px] text-cyan-400">{p}</span>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </Panel>

        <Panel className="p-4">
          <h3 className="font-display font-semibold text-sm text-text-primary mb-3">Patterns</h3>
          {patterns.length === 0 ? (
            <EmptyState title="No patterns mined" description="Experience records will generate patterns" />
          ) : (
            <div className="flex flex-wrap gap-2 max-h-48 overflow-y-auto content-start">
              {patterns.map(p => {
                const size = Math.max(0.7, Math.min(1.5, 0.7 + (p.frequency * 0.2)));
                return (
                  <span
                    key={p.name}
                    className="px-2 py-1 rounded-lg bg-white/5 border border-white/10 text-xs cursor-default transition hover:bg-white/10"
                    style={{ fontSize: `${size * 0.75}rem` }}
                    title={`${p.frequency}x | ${(p.success_rate * 100).toFixed(0)}% success | avg ${p.avg_token_cost.toFixed(0)}t`}
                  >
                    {p.name}
                    <span className="text-text-muted ml-1">×{p.frequency}</span>
                  </span>
                );
              })}
            </div>
          )}
        </Panel>
      </div>

      {/* Compact & task-type breakdown */}
      <div className="grid grid-cols-2 gap-6">
        <Panel className="p-4">
          <h3 className="font-display font-semibold text-sm text-text-primary mb-3">By Task Type</h3>
          {status?.historical?.by_task_type && Object.keys(status.historical.by_task_type).length > 0 ? (
            <div className="space-y-2">
              {Object.entries(status.historical.by_task_type).map(([task, stats]) => (
                <div key={task} className="flex items-center justify-between text-xs p-2 rounded-lg bg-white/5 border border-white/10">
                  <span className="font-medium text-text-primary capitalize">{task}</span>
                  <div className="text-right font-mono">
                    <span className="text-glow-blue">{(stats as { sessions: number; total_tokens: number }).total_tokens.toLocaleString()}t</span>
                    <span className="text-text-muted ml-2">{(stats as { sessions: number; total_tokens: number }).sessions} sessions</span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <EmptyState title="No task data" description="Complete sessions to see task breakdown" />
          )}
        </Panel>

        <Panel className="p-4">
          <h3 className="font-display font-semibold text-sm text-text-primary mb-3">Compaction</h3>
          <div className="space-y-2 text-xs">
            <div className="flex justify-between">
              <span className="text-text-muted">Sessions since last compact</span>
              <span className="font-mono">{status?.sessions_since_compact ?? 0}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-text-muted">Avg tokens per session</span>
              <span className="font-mono">{(status?.historical?.avg_per_session ?? 0).toFixed(0)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-text-muted">Session status</span>
              <span className={`font-mono ${status?.session?.status === 'open' ? 'text-green-400' : 'text-text-muted'}`}>
                {status?.session?.status ?? 'none'}
              </span>
            </div>
            {status?.session?.status === 'open' && status?.session?.id && (
              <div className="mt-3 p-2 rounded-lg bg-cyan-500/10 border border-cyan-500/30">
                <div className="font-medium text-cyan-400 mb-1">Active Session</div>
                <div className="text-text-muted">{(status.session.task as string) || 'unknown task'}</div>
                <div className="text-text-muted font-mono text-[10px]">{status.session.id as string}</div>
              </div>
            )}
          </div>
        </Panel>
      </div>
    </div>
  );
}
