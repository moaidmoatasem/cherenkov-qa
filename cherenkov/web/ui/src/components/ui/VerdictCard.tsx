import type { RichVerdictData } from '../../lib/api';
import DimensionBar from './DimensionBar';

interface VerdictCardProps {
  verdict: RichVerdictData;
  targetUrl?: string;
  timestamp?: string;
  durationMs?: number;
}

const GRADE_TEXT: Record<string, string> = {
  A: 'text-[#22d3ee]',
  B: 'text-blue-400',
  C: 'text-amber-400',
  D: 'text-orange-400',
  F: 'text-red-500',
};

const GRADE_GLOW: Record<string, string> = {
  A: 'drop-shadow-[0_0_20px_rgba(34,211,238,0.5)]',
  B: 'drop-shadow-[0_0_20px_rgba(96,165,250,0.4)]',
  C: 'drop-shadow-[0_0_20px_rgba(251,191,36,0.4)]',
  D: 'drop-shadow-[0_0_20px_rgba(251,146,60,0.4)]',
  F: 'drop-shadow-[0_0_20px_rgba(239,68,68,0.4)]',
};

const OVERALL_STYLE: Record<string, string> = {
  CERTIFIED: 'text-cyan-400 border-cyan-400/40 bg-cyan-400/10',
  DIVERGENT: 'text-red-400 border-red-400/40 bg-red-400/10',
  SUSPECT: 'text-amber-400 border-amber-400/40 bg-amber-400/10',
  INCONCLUSIVE: 'text-slate-400 border-slate-400/40 bg-slate-400/10',
};

const SEVERITY_COLOR: Record<string, string> = {
  critical: 'text-red-400',
  high: 'text-orange-400',
  medium: 'text-amber-400',
  low: 'text-cyan-400',
  info: 'text-slate-400',
};

function fmtMs(ms?: number): string {
  if (!ms) return '';
  return ms >= 1000 ? `${(ms / 1000).toFixed(1)}s` : `${ms}ms`;
}

function fmtTime(ts?: string): string {
  if (!ts) return '';
  try {
    return new Date(ts).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  } catch {
    return ts;
  }
}

export default function VerdictCard({ verdict, targetUrl, timestamp, durationMs }: VerdictCardProps) {
  const gradeText = GRADE_TEXT[verdict.grade] ?? 'text-slate-400';
  const gradeGlow = GRADE_GLOW[verdict.grade] ?? '';
  const overallStyle = OVERALL_STYLE[verdict.overall] ?? 'text-slate-400 border-slate-400/40 bg-slate-400/10';
  const confPct = Math.round(verdict.confidence * 100);

  return (
    <div className="cherenkov-card rounded-xl overflow-hidden">
      {/* Hero header */}
      <div className="px-6 pt-6 pb-4 border-b border-white/10">
        <div className="flex items-start justify-between gap-4">
          {/* Grade */}
          <div className="flex items-baseline gap-4">
            <span className={`font-display font-black text-8xl leading-none select-none ${gradeText} ${gradeGlow}`}>
              {verdict.grade}
            </span>
            <div className="flex flex-col gap-1.5 pt-1">
              <span className={`text-xs font-semibold tracking-widest px-2.5 py-0.5 rounded-full border ${overallStyle}`}>
                {verdict.overall}
              </span>
              <div className="flex items-center gap-1.5">
                <div className="h-1.5 w-20 rounded-full bg-white/5 overflow-hidden">
                  <div
                    className="h-full rounded-full bg-cyan-400/70 transition-all duration-700"
                    style={{ width: `${confPct}%` }}
                  />
                </div>
                <span className="text-[11px] text-slate-400">{confPct}% confidence</span>
              </div>
            </div>
          </div>

          {/* Stats */}
          <div className="text-right text-xs text-slate-500 space-y-0.5 shrink-0">
            {(targetUrl ?? verdict.target_url) && (
              <p className="font-mono text-slate-300 text-xs truncate max-w-[200px]">
                {targetUrl ?? verdict.target_url}
              </p>
            )}
            {timestamp && <p>{fmtTime(timestamp)}</p>}
            {(durationMs ?? verdict.duration_ms) != null && (
              <p>{fmtMs(durationMs ?? verdict.duration_ms)}</p>
            )}
            <p className="text-slate-600">{verdict.divergence_count} divergence{verdict.divergence_count !== 1 ? 's' : ''}</p>
          </div>
        </div>
      </div>

      {/* Dimensions */}
      {verdict.dimensions.length > 0 && (
        <div className="px-6 py-4 border-b border-white/10">
          <h3 className="text-[10px] font-semibold tracking-[0.15em] text-slate-500 uppercase mb-3">Dimensions</h3>
          <div className="space-y-3">
            {verdict.dimensions.map(dim => (
              <DimensionBar
                key={dim.name}
                name={dim.name}
                score={dim.score}
                grade={dim.grade}
                passed={dim.passed}
                findings={dim.findings}
              />
            ))}
          </div>
        </div>
      )}

      {/* Risk flags */}
      {verdict.risk_flags.length > 0 && (
        <div className="px-6 py-3 border-b border-white/10">
          <h3 className="text-[10px] font-semibold tracking-[0.15em] text-slate-500 uppercase mb-2">Risk Flags</h3>
          <div className="flex flex-wrap gap-1.5">
            {verdict.risk_flags.map(flag => (
              <span
                key={flag}
                className="text-[10px] font-mono px-2 py-0.5 rounded-full border border-white/15 bg-white/5 text-slate-300"
              >
                {flag}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Top findings */}
      {verdict.top_findings.length > 0 && (
        <div className="px-6 py-4">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-[10px] font-semibold tracking-[0.15em] text-slate-500 uppercase">Top Findings</h3>
            {verdict.time_to_fix_estimate && verdict.time_to_fix_estimate !== 'none needed' && (
              <span className="text-[10px] text-slate-500">
                fix estimate: <span className="text-slate-300">{verdict.time_to_fix_estimate}</span>
              </span>
            )}
          </div>
          <div className="space-y-2">
            {verdict.top_findings.map(f => (
              <div
                key={f.rank}
                className="flex items-start gap-3 py-2 px-3 rounded-lg bg-white/3 hover:bg-white/5 transition-colors"
              >
                <span className="text-[10px] text-slate-600 font-mono mt-0.5 w-3 shrink-0">{f.rank}</span>
                <span className={`text-[10px] font-semibold uppercase tracking-wide mt-0.5 shrink-0 w-10 ${SEVERITY_COLOR[f.severity] ?? 'text-slate-400'}`}>
                  {f.severity.slice(0, 4).toUpperCase()}
                </span>
                <code className="text-[10px] text-slate-400 font-mono mt-0.5 shrink-0 max-w-[120px] truncate">
                  {f.endpoint}
                </code>
                <div className="flex-1 min-w-0">
                  <p className="text-xs text-slate-200 truncate">{f.summary}</p>
                  {f.remediation && (
                    <p className="text-[10px] text-slate-500 truncate mt-0.5">{f.remediation}</p>
                  )}
                </div>
                {f.estimated_fix_minutes > 0 && (
                  <span className="text-[10px] text-slate-600 shrink-0 mt-0.5">
                    ~{f.estimated_fix_minutes}min
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Empty findings state */}
      {verdict.top_findings.length === 0 && verdict.overall === 'CERTIFIED' && (
        <div className="px-6 py-4 text-center">
          <p className="text-sm text-cyan-400/70">No findings — all dimensions passed</p>
        </div>
      )}
    </div>
  );
}
