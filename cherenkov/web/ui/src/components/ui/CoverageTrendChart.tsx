import React, { useMemo, useState } from 'react';

interface TrendPoint {
  timestamp: string;
  value: number;
}

interface CoverageTrendChartProps {
  points: TrendPoint[];
  height?: number;
}

const WIDTH = 480;
const PAD_X = 8;
const PAD_TOP = 12;
const PAD_BOTTOM = 20;

export function CoverageTrendChart({ points, height = 140 }: CoverageTrendChartProps) {
  const [hoverIndex, setHoverIndex] = useState<number | null>(null);

  const { path, areaPath, coords, gridY } = useMemo(() => {
    const plotWidth = WIDTH - PAD_X * 2;
    const plotHeight = height - PAD_TOP - PAD_BOTTOM;
    const n = points.length;

    const coords = points.map((p, i) => {
      const x = n <= 1 ? PAD_X : PAD_X + (i / (n - 1)) * plotWidth;
      const y = PAD_TOP + (1 - Math.min(100, Math.max(0, p.value)) / 100) * plotHeight;
      return { x, y, ...p };
    });

    const line = coords.map((c, i) => `${i === 0 ? 'M' : 'L'} ${c.x.toFixed(1)} ${c.y.toFixed(1)}`).join(' ');
    const area =
      coords.length > 0
        ? `${line} L ${coords[coords.length - 1].x.toFixed(1)} ${(height - PAD_BOTTOM).toFixed(1)} L ${coords[0].x.toFixed(1)} ${(height - PAD_BOTTOM).toFixed(1)} Z`
        : '';

    const gridY = [0, 50, 100].map((pct) => PAD_TOP + (1 - pct / 100) * plotHeight);

    return { path: line, areaPath: area, coords, gridY };
  }, [points, height]);

  if (points.length === 0) {
    return (
      <div className="text-xs text-text-muted font-mono py-8 text-center">
        No coverage history yet.
      </div>
    );
  }

  const latest = points[points.length - 1];
  const hovered = hoverIndex != null ? coords[hoverIndex] : null;

  return (
    <div className="relative">
      <div className="flex items-baseline justify-between mb-2">
        <span className="text-xs font-mono text-text-muted uppercase tracking-wider">Coverage over time</span>
        <span className="text-sm font-mono font-bold text-glow-bright">{latest.value.toFixed(0)}%</span>
      </div>

      <svg
        viewBox={`0 0 ${WIDTH} ${height}`}
        className="w-full"
        style={{ height }}
        role="img"
        aria-label={`Coverage trend across ${points.length} runs, latest ${latest.value.toFixed(0)}%`}
        onMouseLeave={() => setHoverIndex(null)}
      >
        {/* Faint grid */}
        {gridY.map((y, i) => (
          <line key={i} x1={PAD_X} x2={WIDTH - PAD_X} y1={y} y2={y} className="stroke-white/5" strokeWidth={1} />
        ))}

        {/* Area fill */}
        <path d={areaPath} className="fill-glow-blue/10" />

        {/* Line */}
        <path d={path} className="stroke-glow-blue" strokeWidth={2} fill="none" strokeLinecap="round" strokeLinejoin="round" />

        {/* Emphasized endpoint */}
        {coords.length > 0 && (
          <circle
            cx={coords[coords.length - 1].x}
            cy={coords[coords.length - 1].y}
            r={4}
            className="fill-glow-blue stroke-bg-base"
            strokeWidth={2}
          />
        )}

        {/* Hover targets + crosshair */}
        {coords.map((c, i) => (
          <rect
            key={i}
            x={c.x - (WIDTH / Math.max(coords.length, 1)) / 2}
            y={0}
            width={WIDTH / Math.max(coords.length, 1)}
            height={height}
            fill="transparent"
            onMouseEnter={() => setHoverIndex(i)}
          />
        ))}
        {hovered && (
          <>
            <line x1={hovered.x} x2={hovered.x} y1={PAD_TOP} y2={height - PAD_BOTTOM} className="stroke-white/20" strokeWidth={1} />
            <circle cx={hovered.x} cy={hovered.y} r={4} className="fill-bg-base stroke-glow-blue" strokeWidth={2} />
          </>
        )}
      </svg>

      {hovered && (
        <div
          className="absolute -top-1 px-2 py-1 rounded bg-bg-panel border border-border-custom text-[10px] font-mono text-text-primary pointer-events-none"
          style={{ left: `${(hovered.x / WIDTH) * 100}%`, transform: 'translate(-50%, -100%)' }}
        >
          {hovered.timestamp} &middot; {hovered.value.toFixed(0)}%
        </div>
      )}

      {/* Screen-reader table fallback */}
      <table className="sr-only">
        <caption>Coverage percentage by run timestamp</caption>
        <thead>
          <tr>
            <th>Timestamp</th>
            <th>Coverage %</th>
          </tr>
        </thead>
        <tbody>
          {points.map((p, i) => (
            <tr key={i}>
              <td>{p.timestamp}</td>
              <td>{p.value.toFixed(0)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
