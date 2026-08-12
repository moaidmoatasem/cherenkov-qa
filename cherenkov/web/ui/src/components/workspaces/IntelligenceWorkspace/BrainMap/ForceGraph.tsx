/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 *
 * Canvas force-directed renderer for the brain map.
 *
 * Hand-rolled rather than pulling in d3-force or a graph library: the whole
 * simulation is ~80 lines, the dashboard bundle stays as it is, and the server
 * already caps how many nodes arrive (default 400), which is well inside what
 * a naive O(n²) repulsion handles at 60fps.
 *
 * The canvas is decorative from an accessibility standpoint — every node it
 * draws is also present in the sibling list panel, which is focusable and
 * screen-reader navigable — so it is marked aria-hidden rather than pretending
 * to be an interactive widget.
 */

import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { BrainEdge, BrainNode } from '../../../../lib/api';

export const KIND_COLORS: Record<string, string> = {
  module: '#38bdf8',
  package: '#0ea5e9',
  class: '#a78bfa',
  function: '#c4b5fd',
  component: '#34d399',
  route: '#fbbf24',
  cli_command: '#fb923c',
  doc: '#f472b6',
  adr: '#e879f9',
  test: '#4ade80',
  external: '#94a3b8',
  concept: '#f87171',
};

export const kindColor = (kind: string): string => KIND_COLORS[kind] || '#94a3b8';

interface Particle {
  id: string;
  x: number;
  y: number;
  vx: number;
  vy: number;
  r: number;
  node: BrainNode;
}

interface ForceGraphProps {
  nodes: BrainNode[];
  edges: BrainEdge[];
  selectedId: string | null;
  onSelect: (node: BrainNode) => void;
  height?: number;
}

/** Deterministic pseudo-random in [0, 1) from a string — same layout each load. */
function seeded(id: string): number {
  let hash = 2166136261;
  for (let i = 0; i < id.length; i += 1) {
    hash ^= id.charCodeAt(i);
    hash = Math.imul(hash, 16777619);
  }
  return ((hash >>> 0) % 10000) / 10000;
}

export const ForceGraph: React.FC<ForceGraphProps> = ({
  nodes,
  edges,
  selectedId,
  onSelect,
  height = 460,
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const frameRef = useRef<number>(0);
  const particlesRef = useRef<Particle[]>([]);
  const viewRef = useRef({ zoom: 1, panX: 0, panY: 0 });
  const dragRef = useRef<{ x: number; y: number; panX: number; panY: number } | null>(null);
  const [hovered, setHovered] = useState<BrainNode | null>(null);

  // Links are resolved to particle indices once per data change; doing it per
  // frame is what makes naive force layouts crawl.
  const linkPairs = useMemo(() => {
    const index = new Map(nodes.map((n, i) => [n.id, i]));
    return edges
      .map((e) => ({ a: index.get(e.src), b: index.get(e.dst), kind: e.kind }))
      .filter((l): l is { a: number; b: number; kind: string } => l.a !== undefined && l.b !== undefined);
  }, [nodes, edges]);

  useEffect(() => {
    const maxDegree = Math.max(1, ...nodes.map((n) => n.degree));
    particlesRef.current = nodes.map((node) => {
      const angle = seeded(node.id) * Math.PI * 2;
      const radius = 60 + seeded(node.id + 'r') * 220;
      return {
        id: node.id,
        x: Math.cos(angle) * radius,
        y: Math.sin(angle) * radius,
        vx: 0,
        vy: 0,
        r: 4 + Math.sqrt(node.degree / maxDegree) * 12,
        node,
      };
    });
  }, [nodes]);

  const tick = useCallback(() => {
    const particles = particlesRef.current;
    const count = particles.length;
    if (!count) return;

    // Repulsion — every pair, capped by the server-side node limit.
    for (let i = 0; i < count; i += 1) {
      const a = particles[i];
      for (let j = i + 1; j < count; j += 1) {
        const b = particles[j];
        let dx = b.x - a.x;
        let dy = b.y - a.y;
        let distSq = dx * dx + dy * dy;
        if (distSq < 1) {
          dx = (seeded(a.id + b.id) - 0.5) * 2;
          dy = (seeded(b.id + a.id) - 0.5) * 2;
          distSq = 4;
        }
        const force = 900 / distSq;
        const dist = Math.sqrt(distSq);
        const fx = (dx / dist) * force;
        const fy = (dy / dist) * force;
        a.vx -= fx;
        a.vy -= fy;
        b.vx += fx;
        b.vy += fy;
      }
    }

    // Springs along edges.
    for (const link of linkPairs) {
      const a = particles[link.a];
      const b = particles[link.b];
      if (!a || !b) continue;
      const dx = b.x - a.x;
      const dy = b.y - a.y;
      const dist = Math.sqrt(dx * dx + dy * dy) || 1;
      const force = (dist - 90) * 0.012;
      const fx = (dx / dist) * force;
      const fy = (dy / dist) * force;
      a.vx += fx;
      a.vy += fy;
      b.vx -= fx;
      b.vy -= fy;
    }

    for (const p of particles) {
      p.vx -= p.x * 0.004;
      p.vy -= p.y * 0.004;
      p.vx *= 0.86;
      p.vy *= 0.86;
      p.x += Math.max(-24, Math.min(24, p.vx));
      p.y += Math.max(-24, Math.min(24, p.vy));
    }
  }, [linkPairs]);

  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext('2d');
    if (!canvas || !ctx) return;
    const ratio = window.devicePixelRatio || 1;
    const width = canvas.clientWidth;
    if (canvas.width !== width * ratio || canvas.height !== height * ratio) {
      canvas.width = width * ratio;
      canvas.height = height * ratio;
    }
    const { zoom, panX, panY } = viewRef.current;
    ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
    ctx.clearRect(0, 0, width, height);
    ctx.save();
    ctx.translate(width / 2 + panX, height / 2 + panY);
    ctx.scale(zoom, zoom);

    const particles = particlesRef.current;
    ctx.lineWidth = 1 / zoom;
    for (const link of linkPairs) {
      const a = particles[link.a];
      const b = particles[link.b];
      if (!a || !b) continue;
      const touchesSelection = selectedId === a.id || selectedId === b.id;
      ctx.strokeStyle = touchesSelection ? 'rgba(34,211,238,0.55)' : 'rgba(148,163,184,0.14)';
      ctx.beginPath();
      ctx.moveTo(a.x, a.y);
      ctx.lineTo(b.x, b.y);
      ctx.stroke();
    }

    for (const p of particles) {
      const isSelected = p.id === selectedId;
      const isHovered = hovered?.id === p.id;
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
      ctx.fillStyle = kindColor(p.node.kind);
      ctx.globalAlpha = isSelected || isHovered || !selectedId ? 1 : 0.4;
      ctx.fill();
      if (isSelected || isHovered) {
        ctx.globalAlpha = 1;
        ctx.strokeStyle = '#e2e8f0';
        ctx.lineWidth = 2 / zoom;
        ctx.stroke();
      }
      ctx.globalAlpha = 1;
      if (p.r > 8 || isSelected || isHovered) {
        ctx.fillStyle = 'rgba(226,232,240,0.9)';
        ctx.font = `${Math.max(9, 11 / zoom)}px ui-monospace, monospace`;
        ctx.fillText(p.node.title.slice(0, 28), p.x + p.r + 3, p.y + 3);
      }
    }
    ctx.restore();
  }, [linkPairs, selectedId, hovered, height]);

  useEffect(() => {
    let alive = true;
    const loop = () => {
      if (!alive) return;
      tick();
      draw();
      frameRef.current = requestAnimationFrame(loop);
    };
    frameRef.current = requestAnimationFrame(loop);
    return () => {
      alive = false;
      cancelAnimationFrame(frameRef.current);
    };
  }, [tick, draw]);

  const toWorld = (event: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current!;
    const rect = canvas.getBoundingClientRect();
    const { zoom, panX, panY } = viewRef.current;
    return {
      x: (event.clientX - rect.left - rect.width / 2 - panX) / zoom,
      y: (event.clientY - rect.top - height / 2 - panY) / zoom,
    };
  };

  const hitTest = (event: React.MouseEvent<HTMLCanvasElement>): Particle | null => {
    const { x, y } = toWorld(event);
    let best: Particle | null = null;
    let bestDist = Infinity;
    for (const p of particlesRef.current) {
      const dist = Math.hypot(p.x - x, p.y - y);
      if (dist <= p.r + 4 && dist < bestDist) {
        best = p;
        bestDist = dist;
      }
    }
    return best;
  };

  return (
    <div className="relative rounded-xl border border-white/10 bg-black/40 overflow-hidden">
      <canvas
        ref={canvasRef}
        aria-hidden="true"
        data-testid="brainmap-canvas"
        style={{ width: '100%', height, cursor: dragRef.current ? 'grabbing' : 'grab' }}
        onMouseDown={(e) => {
          const { panX, panY } = viewRef.current;
          dragRef.current = { x: e.clientX, y: e.clientY, panX, panY };
        }}
        onMouseUp={() => {
          dragRef.current = null;
        }}
        onMouseLeave={() => {
          dragRef.current = null;
          setHovered(null);
        }}
        onMouseMove={(e) => {
          const drag = dragRef.current;
          if (drag) {
            viewRef.current.panX = drag.panX + (e.clientX - drag.x);
            viewRef.current.panY = drag.panY + (e.clientY - drag.y);
            return;
          }
          const hit = hitTest(e);
          setHovered(hit ? hit.node : null);
        }}
        onClick={(e) => {
          const hit = hitTest(e);
          if (hit) onSelect(hit.node);
        }}
        onWheel={(e) => {
          const next = viewRef.current.zoom * (e.deltaY < 0 ? 1.12 : 0.89);
          viewRef.current.zoom = Math.max(0.2, Math.min(4, next));
        }}
      />
      {hovered && (
        <div className="absolute top-2 left-2 max-w-sm rounded-lg bg-black/85 border border-white/15 px-3 py-2 pointer-events-none">
          <div className="text-[10px] font-mono uppercase" style={{ color: kindColor(hovered.kind) }}>
            {hovered.kind} · {hovered.degree} links
          </div>
          <div className="text-xs text-text-primary font-mono">{hovered.title}</div>
          {hovered.summary && <div className="text-[11px] text-text-muted mt-0.5">{hovered.summary.slice(0, 120)}</div>}
        </div>
      )}
      <div className="absolute bottom-2 right-3 text-[10px] font-mono text-text-muted pointer-events-none">
        drag to pan · scroll to zoom · click a node
      </div>
    </div>
  );
};

export default ForceGraph;
