import type { RunRecord } from '../../lib/api';

interface RunTimelineProps {
  runs: RunRecord[];
  selectedRunId: string | null;
  onSelect: (run: RunRecord) => void;
}

const GRADE_DOT: Record<string, string> = {
  A: 'bg-cyan-400 border-cyan-400',
  B: 'bg-blue-400 border-blue-400',
  C: 'bg-amber-400 border-amber-400',
  D: 'bg-orange-400 border-orange-400',
  F: 'bg-red-500 border-red-500',
};

const GRADE_TEXT: Record<string, string> = {
  A: 'text-cyan-400',
  B: 'text-blue-400',
  C: 'text-amber-400',
  D: 'text-orange-400',
  F: 'text-red-500',
};

const VERDICT_STYLE: Record<string, string> = {
  CERTIFIED: 'text-cyan-400',
  DIVERGENT: 'text-red-400',
  SUSPECT: 'text-amber-400',
  INCONCLUSIVE: 'text-slate-400',
  PASS: 'text-cyan-400',
  WARN: 'text-amber-400',
  FAIL: 'text-red-400',
};

const GRADE_ORDER: Record<string, number> = { A: 5, B: 4, C: 3, D: 2, F: 1 };

function relativeTime(ts: string): string {
  try {
    const diff = Date.now() - new Date(ts).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return 'just now';
    if (mins < 60) return `${mins}m ago`;
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return `${hrs}h ago`;
    return `${Math.floor(hrs / 24)}d ago`;
  } catch {
    return ts;
  }
}

function trendArrow(prev: RunRecord, curr: RunRecord): string | null {
  const pg = prev.rich_verdict?.grade;
  const cg = curr.rich_verdict?.grade;
  if (!pg || !cg) return null;
  const diff = (GRADE_ORDER[cg] ?? 0) - (GRADE_ORDER[pg] ?? 0);
  if (diff > 0) return '↑';
  if (diff < 0) return '↓';
  return '→';
}

function trendColor(arrow: string | null): string {
  if (arrow === '↑') return 'text-cyan-400';
  if (arrow === '↓') return 'text-red-400';
  return 'text-slate-500';
}

function fmtMs(ms?: number): string {
  if (!ms) return '';
  return ms >= 1000 ? `${(ms / 1000).toFixed(1)}s` : `${ms}ms`;
}

export default function RunTimeline({ runs, selectedRunId, onSelect }: RunTimelineProps) {
  if (runs.length === 0) {
    return (
      <div className="py-12 text-center">
        <p className="text-sm text-slate-500">No runs yet</p>
        <p className="text-xs text-slate-600 mt-1 font-mono">cherenkov verify --url &lt;url&gt;</p>
      </div>
    );
  }

  return (
    <div className="space-y-0">
      {runs.map((run, idx) => {
        const grade = run.rich_verdict?.grade;
        const isSelected = run.run_id === selectedRunId;
        const dotClass = grade ? (GRADE_DOT[grade] ?? 'bg-slate-500 border-slate-500') : 'bg-slate-600 border-slate-600';
        const gradeTextClass = grade ? (GRADE_TEXT[grade] ?? 'text-slate-400') : 'text-slate-400';
        const verdictStyle = VERDICT_STYLE[run.verdict] ?? 'text-slate-400';
        const nextRun = runs[idx + 1];
        const arrow = nextRun ? trendArrow(nextRun, run) : null;

        return (
          <div key={run.run_id} className="relative flex gap-3">
            {/* Timeline spine */}
            <div className="flex flex-col items-center shrink-0">
              <div className={`w-3 h-3 rounded-full border-2 mt-1 shrink-0 ${dotClass} ${isSelected ? 'ring-2 ring-white/20 ring-offset-1 ring-offset-[#020617]' : ''}`} />
              {idx < runs.length - 1 && (
                <div className="w-px flex-1 bg-white/10 mt-0.5 mb-0" style={{ minHeight: 28 }} />
              )}
            </div>

            {/* Node content */}
            <button
              className={`flex-1 text-left pb-4 pr-2 rounded-lg transition-colors ${isSelected ? 'opacity-100' : 'opacity-70 hover:opacity-90'}`}
              onClick={() => onSelect(run)}
            >
              <div className="flex items-center gap-2 flex-wrap">
                {grade ? (
                  <span className={`text-sm font-bold font-mono ${gradeTextClass}`}>{grade}</span>
                ) : null}
                <span className={`text-xs font-semibold ${verdictStyle}`}>{run.verdict || '—'}</span>
                {arrow && (
                  <span className={`text-xs ${trendColor(arrow)}`}>{arrow}</span>
                )}
                <span className="text-[11px] text-slate-500 ml-auto">{relativeTime(run.timestamp)}</span>
              </div>
              <div className="flex items-center gap-2 mt-0.5 flex-wrap">
                {run.coverage_pct != null && (
                  <span className="text-[10px] text-slate-500 font-mono">{run.coverage_pct.toFixed(0)}% cov</span>
                )}
                {run.divergence_count > 0 && (
                  <span className="text-[10px] text-slate-500">{run.divergence_count} div</span>
                )}
                {run.duration_ms > 0 && (
                  <span className="text-[10px] text-slate-600 font-mono">{fmtMs(run.duration_ms)}</span>
                )}
              </div>
              {run.target_url && (
                <p className="text-[10px] text-slate-600 font-mono truncate mt-0.5">{run.target_url}</p>
              )}
            </button>
          </div>
        );
      })}
    </div>
  );
}
