/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useRef, useEffect } from 'react';
import { Upload, Globe, CheckCircle, AlertCircle, RefreshCw, Folder, ArrowRight } from 'lucide-react';
import { Card } from '../../ui';
import { ingestSpec, fetchProjects, IngestResponse } from '../../../lib/api';
import { Project, EndpointRichness } from '../../../types';

interface SpecIngestPanelProps {
  onSpecIngested?: (specPath: string, endpoints: EndpointRichness[]) => void;
  /** Runs the pipeline for the spec just ingested. */
  onGenerate?: () => void;
  generating?: boolean;
}

/** Richness bands, worst first — a degraded endpoint is the one worth acting on. */
const BANDS: { key: EndpointRichness['band']; label: string; className: string }[] = [
  { key: 'degraded', label: 'degraded', className: 'text-rose-400' },
  { key: 'inferred', label: 'inferred', className: 'text-amber-400' },
  { key: 'full', label: 'full', className: 'text-emerald-400' },
];

export const SpecIngestPanel: React.FC<SpecIngestPanelProps> = ({
  onSpecIngested,
  onGenerate,
  generating = false,
}) => {
  const [dragActive, setDragActive] = useState(false);
  const [fileName, setFileName] = useState<string | null>(null);
  const [specUrl, setSpecUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedRepoSpec, setSelectedRepoSpec] = useState<string>('');
  // The ingest response scores every endpoint for richness. That was being
  // computed, lifted to the workspace and then never rendered, so a successful
  // ingest showed only "Ingestion complete" with no forward path.
  const [endpoints, setEndpoints] = useState<EndpointRichness[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Auto-detect project spec paths from live /api/v1/projects
  useEffect(() => {
    fetchProjects()
      .then((data) => {
        setProjects(data || []);
      })
      .catch(() => setProjects([]));
  }, []);

  const handleIngest = async (name: string, file: File | null, url: string | null) => {
    setLoading(true);
    setError(null);
    setFileName(name);
    setEndpoints([]);
    try {
      const data: IngestResponse = await ingestSpec(file, url);
      const mappedEndpoints: EndpointRichness[] = (data.endpoints || []).map((ep: any, idx: number) => ({
        id: `ep-${idx}`,
        path: ep.path,
        method: ep.method,
        richness: ep.richness,
        band: (ep.richness >= 0.7 ? 'full' : ep.richness >= 0.5 ? 'inferred' : 'degraded') as 'full' | 'inferred' | 'degraded',
        missingElements: ep.missing_elements || [],
      }));

      setEndpoints(mappedEndpoints);
      if (onSpecIngested) {
        onSpecIngested(data.spec_path, mappedEndpoints);
      }
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  };

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') setDragActive(true);
    else if (e.type === 'dragleave') setDragActive(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      handleIngest(file.name, file, null);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      handleIngest(file.name, file, null);
    }
  };

  const handleUrlSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (specUrl.trim()) {
      handleIngest(specUrl, null, specUrl);
    }
  };

  return (
    <Card className="p-6 space-y-6" data-testid="spec-ingest-panel">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold font-mono uppercase tracking-wider text-text-muted flex items-center gap-2">
            <Upload className="w-4 h-4 text-cyan-400" />
            <span>OpenAPI Spec Ingestion</span>
          </h2>
          <p className="text-xs text-text-muted mt-0.5">
            Drag-and-drop OpenAPI spec files or auto-detect repository project specs.
          </p>
        </div>
      </div>

      {/* Auto-detected Repository Spec Selector */}
      {projects.length > 0 && (
        <div className="p-3 bg-black/20 border border-white/5 rounded-xl flex items-center justify-between text-xs font-mono">
          <div className="flex items-center gap-2">
            <Folder className="w-4 h-4 text-cyan-400" />
            <span className="text-text-muted">Detected Project Specs:</span>
          </div>
          <select
            value={selectedRepoSpec}
            aria-label="Select a detected project spec to ingest"
            onChange={(e) => {
              setSelectedRepoSpec(e.target.value);
              if (e.target.value) {
                handleIngest(e.target.value, null, e.target.value);
              }
            }}
            className="bg-bg-base border border-border-subtle rounded-lg px-2 py-1 text-cyan-400 text-xs font-mono focus:outline-none"
          >
            <option value="">-- Select Project Spec --</option>
            {projects.map((p) => (
              <option key={p.id} value={p.name}>
                {p.name} ({p.stats?.testsCount || 0} tests)
              </option>
            ))}
          </select>
        </div>
      )}

      {/* Drag & Drop Upload Box */}
      <div
        onDragEnter={handleDrag}
        onDragOver={handleDrag}
        onDragLeave={handleDrag}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all duration-300 ${
          dragActive
            ? 'border-cyan-400 bg-cyan-500/10'
            : fileName
            ? 'border-emerald-500/50 bg-emerald-500/5'
            : 'border-white/10 hover:border-cyan-400/50 bg-black/30'
        }`}
        data-testid="spec-drop-zone"
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".json,.yaml,.yml"
          onChange={handleFileChange}
          className="hidden"
        />
        <div className="flex flex-col items-center gap-3">
          <div className={`p-3 rounded-full ${fileName ? 'bg-emerald-500/20 text-emerald-400' : 'bg-white/5 text-text-muted'}`}>
            <Upload className="w-6 h-6" />
          </div>
          {loading ? (
            <p className="text-xs font-mono text-cyan-400 animate-pulse flex items-center gap-2">
              <RefreshCw className="w-4 h-4 animate-spin" /> Ingesting and parsing richness metrics...
            </p>
          ) : fileName ? (
            <div>
              <p className="text-xs font-mono font-bold text-text-primary">{fileName}</p>
              <p className="text-[10px] font-mono text-emerald-400 mt-1 flex items-center justify-center gap-1">
                <CheckCircle className="w-3 h-3" /> Ingestion complete
              </p>
            </div>
          ) : (
            <div>
              <p className="text-xs font-semibold text-text-primary">Drag & Drop OpenAPI Spec (.json / .yaml)</p>
              <p className="text-[10px] text-text-muted mt-1">Accepts OpenAPI 2.0 / 3.0 / 3.1 definitions</p>
            </div>
          )}
        </div>
      </div>

      {/* What was actually ingested, and the way forward. A green "complete"
          tick with no result and no next action left the primary workflow of
          the primary screen dead-ending on success. */}
      {!loading && endpoints.length > 0 && (
        <div
          className="p-4 bg-black/20 border border-white/10 rounded-xl space-y-3"
          data-testid="ingest-summary"
        >
          <div className="flex items-baseline justify-between gap-3 flex-wrap">
            <p className="text-xs font-mono text-text-primary">
              <span className="text-lg font-bold text-cyan-400 tabular-nums">
                {endpoints.length}
              </span>{' '}
              endpoint{endpoints.length === 1 ? '' : 's'} ready to generate from
            </p>
            <div className="flex gap-3 text-[10px] font-mono">
              {BANDS.map(({ key, label, className }) => {
                const n = endpoints.filter((e) => e.band === key).length;
                if (!n) return null;
                return (
                  <span key={key} className={className}>
                    {n} {label}
                  </span>
                );
              })}
            </div>
          </div>

          {endpoints.some((e) => e.band === 'degraded') && (
            <p className="text-[10px] font-mono text-text-muted leading-relaxed">
              Degraded endpoints lack the response detail needed for strong
              assertions — tests generated for them will be weaker.
            </p>
          )}

          {onGenerate && (
            <button
              type="button"
              onClick={onGenerate}
              disabled={generating}
              data-testid="generate-suite-btn"
              className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-cyan-400 hover:bg-cyan-300 disabled:opacity-50 disabled:cursor-not-allowed text-bg-base rounded-lg text-xs font-mono font-bold transition"
            >
              {generating ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" /> Generating suite...
                </>
              ) : (
                <>
                  Generate test suite <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          )}
        </div>
      )}

      {/* Spec URL alternative */}
      <form onSubmit={handleUrlSubmit} className="flex gap-2">
        <div className="relative flex-1">
          <Globe className="absolute left-3 top-2.5 w-4 h-4 text-text-muted" />
          <input
            type="url"
            placeholder="https://api.example.com/openapi.json"
            value={specUrl}
            onChange={(e) => setSpecUrl(e.target.value)}
            className="w-full bg-bg-base text-text-primary text-xs pl-9 pr-3 py-2 rounded-lg border border-white/10 focus:outline-none focus:border-cyan-400 font-mono"
          />
        </div>
        <button
          type="submit"
          disabled={loading || !specUrl.trim()}
          className="px-4 py-2 bg-white/5 hover:bg-white/10 text-cyan-400 border border-white/10 rounded-lg text-xs font-mono font-semibold transition"
        >
          Fetch
        </button>
      </form>

      {error && (
        <div className="p-3 bg-rose-500/10 border border-rose-500/30 rounded-xl text-xs text-rose-400 flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>Ingestion failed: {error}</span>
        </div>
      )}
    </Card>
  );
};

export default SpecIngestPanel;
