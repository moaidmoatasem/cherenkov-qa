import { useEffect, useState } from 'react';

interface DimensionBarProps {
  name: string;
  score: number;
  grade: string;
  passed: boolean;
  findings?: string[];
}

const GRADE_COLORS: Record<string, string> = {
  A: 'bg-cyan-400',
  B: 'bg-blue-400',
  C: 'bg-amber-400',
  D: 'bg-orange-400',
  F: 'bg-red-500',
};

const GRADE_TEXT: Record<string, string> = {
  A: 'text-cyan-400',
  B: 'text-blue-400',
  C: 'text-amber-400',
  D: 'text-orange-400',
  F: 'text-red-500',
};

const LABEL_MAP: Record<string, string> = {
  divergence_probe: 'Divergence Probe',
  spec_coverage: 'Spec Coverage',
  mutation_oracle: 'Mutation Oracle',
  semantic_judge: 'Semantic Judge',
  traffic_capture: 'Traffic Capture',
};

export default function DimensionBar({ name, score, grade, passed, findings }: DimensionBarProps) {
  const [width, setWidth] = useState(0);

  useEffect(() => {
    setWidth(0);
    const t = setTimeout(() => setWidth(Math.round(score * 100)), 80);
    return () => clearTimeout(t);
  }, [score]);

  const barColor = GRADE_COLORS[grade] ?? (passed ? 'bg-cyan-400' : 'bg-red-500');
  const textColor = GRADE_TEXT[grade] ?? 'text-slate-400';
  const label = LABEL_MAP[name] ?? name.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());

  return (
    <div className="group">
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs text-slate-400 font-mono tracking-wide">{label}</span>
        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-500">{(score * 100).toFixed(0)}%</span>
          <span className={`text-xs font-bold font-mono ${textColor}`}>{grade}</span>
          {!passed && (
            <span className="text-[10px] text-red-400 border border-red-400/40 rounded px-1">FAIL</span>
          )}
        </div>
      </div>
      <div className="relative h-1.5 rounded-full bg-white/5 overflow-hidden">
        <div
          className={`absolute inset-y-0 left-0 rounded-full ${barColor} opacity-80 transition-all duration-700 ease-out`}
          style={{ width: `${width}%` }}
        />
      </div>
      {findings && findings.length > 0 && (
        <div className="mt-1 hidden group-hover:block">
          {findings.slice(0, 2).map((f, i) => (
            <p key={i} className="text-[10px] text-slate-500 font-mono truncate">· {f}</p>
          ))}
        </div>
      )}
    </div>
  );
}
