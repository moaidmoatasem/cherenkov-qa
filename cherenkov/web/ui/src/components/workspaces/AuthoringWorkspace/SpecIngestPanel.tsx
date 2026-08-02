/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useRef, useEffect } from 'react';
import { Upload, Globe, CheckCircle, AlertCircle, RefreshCw, Folder } from 'lucide-react';
import { Card } from '../../ui';
import { ingestSpec, fetchProjects, IngestResponse } from '../../../lib/api';
import { Project, EndpointRichness } from '../../../types';

interface SpecIngestPanelProps {
  onSpecIngested?: (specPath: string, endpoints: EndpointRichness[]) => void;
}

export const SpecIngestPanel: React.FC<SpecIngestPanelProps> = ({ onSpecIngested }) => {
  const [dragActive, setDragActive] = useState(false);
  const [fileName, setFileName] = useState<string | null>(null);
  const [specUrl, setSpecUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedRepoSpec, setSelectedRepoSpec] = useState<string>('');
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
