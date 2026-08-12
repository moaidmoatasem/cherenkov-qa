/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 *
 * Brain Map panel — the codebase as a navigable graph, inside the dashboard.
 *
 * Three views over one map: the force graph (shape), the node list (precise
 * navigation and the accessible path to everything the canvas draws), and the
 * findings list (what reconciliation could not resolve). Selecting a node
 * pivots the graph to its neighbourhood, which is how you actually explore a
 * repository — start somewhere you know, walk outward.
 */

import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Card, EmptyState, Skeleton } from '../../../ui';
import {
  BrainFinding,
  BrainGraph,
  BrainNode,
  BrainStatus,
  exportBrainVault,
  getBrainFindings,
  getBrainGraph,
  getBrainNeighborhood,
  getBrainStatus,
  syncBrainMap,
} from '../../../../lib/api';
import ForceGraph, { kindColor } from './ForceGraph';
import {
  Brain,
  Download,
  Focus,
  RefreshCw,
  Search,
  TriangleAlert,
  X,
} from 'lucide-react';

const SEVERITY_STYLE: Record<string, string> = {
  error: 'text-rose-400 border-rose-500/40 bg-rose-500/10',
  warn: 'text-amber-400 border-amber-500/40 bg-amber-500/10',
  info: 'text-cyan-400 border-cyan-500/40 bg-cyan-500/10',
};

export const BrainMapPanel: React.FC = () => {
  const [status, setStatus] = useState<BrainStatus | null>(null);
  const [graph, setGraph] = useState<BrainGraph | null>(null);
  const [findings, setFindings] = useState<BrainFinding[]>([]);
  const [findingCodes, setFindingCodes] = useState<Record<string, number>>({});
  const [selected, setSelected] = useState<BrainNode | null>(null);
  const [focusId, setFocusId] = useState<string | null>(null);
  const [kinds, setKinds] = useState<string[]>([]);
  const [search, setSearch] = useState('');
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const loadGraph = useCallback(async () => {
    setError(null);
    try {
      const data = focusId
        ? await getBrainNeighborhood(focusId, 2)
        : await getBrainGraph({ limit: 300, kinds, q: search });
      setGraph(data);
    } catch (err) {
      setError((err as Error).message);
    }
  }, [focusId, kinds, search]);

  const loadAll = useCallback(async () => {
    setLoading(true);
    try {
      const [statusData, findingsData] = await Promise.all([getBrainStatus(), getBrainFindings({ limit: 60 })]);
      setStatus(statusData);
      setFindings(findingsData.findings);
      setFindingCodes(findingsData.by_code);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
    await loadGraph();
  }, [loadGraph]);

  useEffect(() => {
    void loadAll();
    // loadAll changes with the filters; re-running on that is the intent.
  }, [loadAll]);

  const runSync = async (full: boolean) => {
    setBusy(true);
    setNotice(null);
    try {
      const report = await syncBrainMap(full);
      if (report.busy) {
        setNotice('A sync is already running.');
      } else {
        setNotice(
          `${full ? 'Rebuilt' : 'Synced'}: ${report.parsed ?? 0} parsed, ${report.skipped ?? 0} unchanged` +
            ` in ${report.duration_ms ?? 0} ms`
        );
        await loadAll();
      }
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const runExport = async () => {
    setBusy(true);
    setNotice(null);
    try {
      const result = await exportBrainVault();
      setNotice(`Vault written: ${result.notes_written} notes → ${result.vault}`);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const stats = status?.stats;
  const availableKinds = useMemo(() => Object.keys(stats?.by_kind || {}).sort(), [stats]);
  const toggleKind = (kind: string) =>
    setKinds((current) => (current.includes(kind) ? current.filter((k) => k !== kind) : [...current, kind]));

  if (loading && !graph) {
    return (
      <Card className="p-6 space-y-4">
        <Skeleton className="h-6 w-64 rounded" />
        <Skeleton className="h-96 rounded-xl" />
      </Card>
    );
  }

  if (status && !status.exists) {
    return (
      <Card className="p-6" data-testid="brainmap-empty">
        <EmptyState
          icon={Brain}
          title="No brain map yet"
          description="Build the map to see this repository as a graph of modules, routes, commands, docs and tests."
        />
        <div className="flex justify-center">
          <button
            onClick={() => void runSync(true)}
            disabled={busy}
            className="px-4 py-2 bg-cyan-500/20 text-cyan-400 border border-cyan-500/40 rounded-lg text-xs font-mono font-bold flex items-center gap-2 disabled:opacity-50"
            data-testid="brainmap-build"
          >
            <RefreshCw className={`w-4 h-4 ${busy ? 'animate-spin' : ''}`} /> Build the map
          </button>
        </div>
      </Card>
    );
  }

  return (
    <Card className="p-6 space-y-4" data-testid="brainmap-panel">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h2 className="text-sm font-semibold font-mono uppercase tracking-wider text-text-muted flex items-center gap-2">
            <Brain className="w-4 h-4 text-cyan-400" />
            <span>Brain Map</span>
          </h2>
          <p className="text-xs text-text-muted mt-0.5">
            {stats
              ? `${stats.nodes} nodes · ${stats.edges} edges · ${stats.files} files · built ${stats.built_at}`
              : 'Reconciled map of this repository.'}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => void runSync(false)}
            disabled={busy}
            className="px-3 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-[11px] font-mono flex items-center gap-1.5 disabled:opacity-50"
            data-testid="brainmap-sync"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${busy ? 'animate-spin' : ''}`} /> Sync
          </button>
          <button
            onClick={() => void runExport()}
            disabled={busy}
            className="px-3 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-[11px] font-mono flex items-center gap-1.5 disabled:opacity-50"
            data-testid="brainmap-export"
          >
            <Download className="w-3.5 h-3.5" /> Export vault
          </button>
        </div>
      </div>

      {notice && (
        <div className="p-2.5 rounded-lg bg-cyan-500/10 border border-cyan-500/30 text-[11px] font-mono text-cyan-300">
          {notice}
        </div>
      )}
      {error && (
        <div className="p-2.5 rounded-lg bg-rose-500/10 border border-rose-500/30 text-[11px] font-mono text-rose-400">
          {error}
        </div>
      )}

      <div className="flex flex-wrap items-center gap-2">
        <div className="relative flex-1 min-w-[220px]">
          <Search className="absolute left-3 top-2.5 w-4 h-4 text-text-muted" />
          <input
            type="text"
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setFocusId(null);
            }}
            placeholder="Filter nodes by name or summary…"
            className="w-full bg-bg-base text-text-primary text-xs pl-9 pr-3 py-2 rounded-lg border border-white/10 focus:outline-none focus:border-cyan-400 font-mono"
            data-testid="brainmap-search"
          />
        </div>
        {focusId && (
          <button
            onClick={() => setFocusId(null)}
            className="px-2.5 py-1.5 rounded-lg bg-cyan-500/10 border border-cyan-500/30 text-[11px] font-mono text-cyan-300 flex items-center gap-1"
          >
            <X className="w-3 h-3" /> Clear focus
          </button>
        )}
      </div>

      <div className="flex flex-wrap gap-1.5">
        {availableKinds.map((kind) => {
          const active = kinds.includes(kind);
          return (
            <button
              key={kind}
              onClick={() => {
                toggleKind(kind);
                setFocusId(null);
              }}
              className={`px-2 py-1 rounded-full border text-[10px] font-mono transition ${
                active ? 'bg-white/10 border-white/30 text-text-primary' : 'border-white/10 text-text-muted'
              }`}
              data-testid={`brainmap-kind-${kind}`}
            >
              <span
                className="inline-block w-2 h-2 rounded-full mr-1.5 align-middle"
                style={{ backgroundColor: kindColor(kind) }}
              />
              {kind} {stats?.by_kind[kind] ?? 0}
            </button>
          );
        })}
      </div>

      {graph && graph.nodes.length > 0 ? (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <div className="lg:col-span-2">
            <ForceGraph
              nodes={graph.nodes}
              edges={graph.edges}
              selectedId={selected?.id ?? null}
              onSelect={setSelected}
            />
            {graph.truncated.nodes_hidden > 0 && (
              <p className="text-[10px] font-mono text-text-muted mt-1.5">
                Showing the {graph.nodes.length} most connected of {graph.truncated.matched} matching nodes
                ({graph.truncated.nodes_hidden} hidden). Narrow the filters to see the rest.
              </p>
            )}
          </div>

          <div className="space-y-3">
            {selected ? (
              <div className="rounded-xl border border-white/10 bg-black/30 p-3 space-y-2" data-testid="brainmap-detail">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <div className="text-[10px] font-mono uppercase" style={{ color: kindColor(selected.kind) }}>
                      {selected.kind}
                      {selected.layer ? ` · ${selected.layer}` : ''}
                    </div>
                    <div className="text-xs font-mono text-text-primary break-all">{selected.title}</div>
                  </div>
                  <button onClick={() => setSelected(null)} className="text-text-muted hover:text-text-primary">
                    <X className="w-3.5 h-3.5" />
                  </button>
                </div>
                {selected.summary && <p className="text-[11px] text-text-muted leading-relaxed">{selected.summary}</p>}
                {selected.origin && (
                  <p className="text-[10px] font-mono text-text-muted break-all">{selected.origin}</p>
                )}
                <button
                  onClick={() => setFocusId(selected.id)}
                  className="w-full px-2.5 py-1.5 rounded-lg bg-cyan-500/10 hover:bg-cyan-500/20 text-cyan-400 border border-cyan-500/30 text-[10px] font-mono font-bold flex items-center justify-center gap-1.5"
                  data-testid="brainmap-focus"
                >
                  <Focus className="w-3 h-3" /> Focus neighbourhood
                </button>
              </div>
            ) : (
              <div className="rounded-xl border border-white/10 bg-black/20 p-3 text-[11px] text-text-muted font-mono">
                Select a node in the graph or the list below.
              </div>
            )}

            <div className="rounded-xl border border-white/10 bg-black/20 max-h-64 overflow-y-auto">
              <ul data-testid="brainmap-node-list">
                {graph.nodes.slice(0, 120).map((node) => (
                  <li key={node.id}>
                    <button
                      onClick={() => setSelected(node)}
                      className={`w-full text-left px-3 py-1.5 text-[11px] font-mono flex items-center gap-2 hover:bg-white/5 ${
                        selected?.id === node.id ? 'bg-white/10' : ''
                      }`}
                    >
                      <span
                        className="w-2 h-2 rounded-full shrink-0"
                        style={{ backgroundColor: kindColor(node.kind) }}
                      />
                      <span className="truncate text-text-primary">{node.title}</span>
                      <span className="ml-auto text-text-muted">{node.degree}</span>
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      ) : (
        <EmptyState
          icon={Search}
          title="Nothing matches those filters"
          description="Clear the search box or re-enable a node kind."
        />
      )}

      <div className="space-y-2">
        <h3 className="text-xs font-mono uppercase tracking-wider text-text-muted flex items-center gap-2">
          <TriangleAlert className="w-3.5 h-3.5 text-amber-400" />
          Reconciliation findings
          {stats?.findings ? <span className="text-text-muted">({stats.findings})</span> : null}
        </h3>
        <div className="flex flex-wrap gap-1.5">
          {Object.entries(findingCodes).map(([code, count]) => (
            <span
              key={code}
              className="px-2 py-0.5 rounded-full border border-white/10 text-[10px] font-mono text-text-muted"
            >
              {code} {count}
            </span>
          ))}
        </div>
        <div className="rounded-xl border border-white/10 bg-black/20 max-h-56 overflow-y-auto divide-y divide-white/5">
          {findings.length === 0 ? (
            <p className="p-3 text-[11px] font-mono text-text-muted">
              Every reference in this map resolves.
            </p>
          ) : (
            findings.map((finding, index) => (
              <div key={`${finding.code}-${index}`} className="px-3 py-2 flex items-start gap-2">
                <span
                  className={`px-1.5 py-0.5 rounded border text-[9px] font-mono uppercase shrink-0 ${
                    SEVERITY_STYLE[finding.severity] || SEVERITY_STYLE.info
                  }`}
                >
                  {finding.severity}
                </span>
                <div className="min-w-0">
                  <div className="text-[11px] font-mono text-text-primary truncate">{finding.message}</div>
                  {finding.origin && (
                    <div className="text-[10px] font-mono text-text-muted truncate">{finding.origin}</div>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </Card>
  );
};

export default BrainMapPanel;
