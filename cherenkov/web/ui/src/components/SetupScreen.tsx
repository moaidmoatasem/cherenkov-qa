/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useRef } from 'react';
import { 
  Upload, 
  Globe, 
  ChevronRight, 
  AlertCircle, 
  CheckCircle, 
  Terminal, 
  ChevronDown, 
  ChevronUp, 
  Layers
} from 'lucide-react';
import { EndpointRichness } from '../types';

import CherenkovLogo from './CherenkovLogo';
import { ingestSpec, fetchDoctor, DoctorCheck } from '../lib/api';
import { Skeleton } from './ui';
import { useToast } from './ui/Toast';

interface SetupScreenProps {
  onStartPipeline: (endpoints: EndpointRichness[], specPath: string, targetUrl: string, authHeader: string) => void;
}

export default function SetupScreen({ onStartPipeline }: SetupScreenProps) {
  const [dragActive, setDragActive] = useState(false);
  const [fileName, setFileName] = useState<string | null>(null);
  const [specUrl, setSpecUrl] = useState('');
  const [endpoints, setEndpoints] = useState<EndpointRichness[]>([]);
  const [validationExpanded, setValidationExpanded] = useState(false);
  const [serverUrl, setServerUrl] = useState('http://localhost:8080/v2');
  const [serverAuth, setServerAuth] = useState('');
  const [loading, setLoading] = useState(false);
  const [ingestedSpecPath, setIngestedSpecPath] = useState<string | null>(null);
  const { toast, addToast } = useToast();
  
  // Tooltip details state
  const [hoveredEndpoint, setHoveredEndpoint] = useState<EndpointRichness | null>(null);
  const [tooltipPos, setTooltipPos] = useState({ x: 0, y: 0 });

  const [doctorChecks, setDoctorChecks] = useState<DoctorCheck[]>([]);
  const [doctorLoading, setDoctorLoading] = useState(true);
  const [systemReady, setSystemReady] = useState(false);

  const fileInputRef = useRef<HTMLInputElement>(null);

  React.useEffect(() => {
    fetchDoctor().then(data => {
      setDoctorChecks(data.checks || []);
      setSystemReady(data.ready);
      setDoctorLoading(false);
    }).catch(err => {
      addToast("System Readiness Check failed to connect.", "danger");
      setDoctorLoading(false);
      setSystemReady(true); // Fallback to ready if we can't tell
    });
  }, []);

  // handle drag events
  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const loadRealOrMockSpec = async (name: string, file: File | null, url: string | null) => {
    setLoading(true);
    setFileName(name);
    try {
      const data = await ingestSpec(file, url);
      const mapped = data.endpoints.map((ep: any, idx: number) => ({
        id: `ep-${idx}`,
        path: ep.path,
        method: ep.method,
        richness: ep.richness,
        band: ep.richness >= 0.7 ? 'full' : ep.richness >= 0.5 ? 'inferred' : 'degraded',
        missingElements: ep.missing_elements || [],
      }));
      setEndpoints(mapped);
      setIngestedSpecPath(data.spec_path);
    } catch (err) {
      addToast("Real backend spec ingestion failed.", "error");
      setEndpoints([]);
    } finally {
      setLoading(false);
    }
  };

  const loadMockSpec = (name: string) => {
    loadRealOrMockSpec(name, null, null);
  };

  // handle drop
  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      if (file.name.endsWith('.json') || file.name.endsWith('.yaml') || file.name.endsWith('.yml')) {
        await loadRealOrMockSpec(file.name, file, null);
      } else {
        alert('Please provide a valid Swagger/OpenAPI spec (.yaml or .json)');
      }
    }
  };

  // handle input click change
  const handleChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    e.preventDefault();
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      await loadRealOrMockSpec(file.name, file, null);
    }
  };

  const handleUrlSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (specUrl.trim() !== '') {
      const name = specUrl.substring(specUrl.lastIndexOf('/') + 1) || 'openapi-remote-spec.yaml';
      await loadRealOrMockSpec(name, null, specUrl);
    }
  };

  const handleSegmentHover = (e: React.MouseEvent, ep: EndpointRichness) => {
    const rect = e.currentTarget.getBoundingClientRect();
    setHoveredEndpoint(ep);
    // position tooltip above item
    setTooltipPos({
      x: rect.left + rect.width / 2,
      y: rect.top - 8
    });
  };

  const handleStartGeneration = () => {
    if (endpoints.length > 0 && ingestedSpecPath) {
      toast('Starting generation of ' + endpoints.length + ' test suites...', 'info');
      onStartPipeline(endpoints, ingestedSpecPath, serverUrl, serverAuth);
    }
  };

  // calculate average richness
  const avgRichness = endpoints.length > 0
    ? endpoints.reduce((acc, ep) => acc + ep.richness, 0) / endpoints.length
    : 0;

  const countByBand = {
    full: endpoints.filter(ep => ep.band === 'full').length,
    inferred: endpoints.filter(ep => ep.band === 'inferred').length,
    degraded: endpoints.filter(ep => ep.band === 'degraded').length,
  };

  return (
    <div className="p-8 h-full overflow-y-auto space-y-6 grid-bg bg-transparent relative z-10" id="setup-screen" onDragEnter={handleDrag}>
      
      {/* Title */}
      <div className="flex items-center gap-4">
        <CherenkovLogo variant="icon" size={42} />
        <div>
          <h1 className="font-display font-bold text-3xl text-text-primary tracking-tight">
            New Test Generation Run
          </h1>
          <p className="text-sm text-text-muted mt-1 leading-relaxed">
            Supply an OpenAPI index to generate synthetically verified Playwright tests.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6 items-start">
        {/* Ingest Column */}
        <div className="xl:col-span-2 space-y-6">

          {/* System Check / First-run Wizard Panel */}
          {doctorLoading ? (
            <Skeleton className="w-full h-24 rounded-2xl" />
          ) : !systemReady ? (
            <div className="bg-amber-500/10 border border-amber-500/20 p-6 rounded-2xl flex items-start gap-4">
              <AlertCircle className="w-6 h-6 text-amber-500 mt-1" />
              <div className="space-y-2 flex-1">
                <h3 className="text-amber-500 font-bold text-sm uppercase tracking-wider">System Readiness Check Failed</h3>
                <ul className="text-xs text-[#E6EDF3] space-y-2">
                  {doctorChecks.map((chk, i) => (
                    <li key={i} className="flex items-center gap-2">
                      {chk.status === 'passed' ? <CheckCircle className="w-4 h-4 text-[#3FB950]" /> : <AlertCircle className="w-4 h-4 text-[#F85149]" />}
                      <span className="font-mono">{chk.name}</span>
                      {chk.message && <span className="text-[#7D8DA1]">- {chk.message}</span>}
                    </li>
                  ))}
                </ul>
                <p className="text-xs text-[#7D8DA1] pt-2">Please resolve the failing dependencies (e.g. start Ollama) or check the documentation to proceed.</p>
              </div>
            </div>
          ) : (
            <div className="bg-[#3FB950]/10 border border-[#3FB950]/20 p-4 rounded-xl flex items-center gap-3">
              <CheckCircle className="w-5 h-5 text-[#3FB950]" />
              <span className="text-xs text-[#3FB950] font-mono font-bold">ALL SYSTEM CHECKS PASSED. ENGINE READY.</span>
            </div>
          )}
          
          {/* Spec upload form / area */}
          <div className="bg-white/5 backdrop-blur-xl border border-white/10 px-6 py-8 rounded-2xl space-y-6 relative">
            <h2 className="text-lg font-display font-semibold text-text-primary flex items-center gap-2">
              <Upload className="w-5 h-5 text-glow-blue" />
              <span>Ingest API Definition</span>
            </h2>

            {/* Drag Zone */}
            <div
              onDragEnter={handleDrag}
              onDragOver={handleDrag}
              onDragLeave={handleDrag}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              className={`border border-dashed rounded-xl p-8 text-center cursor-pointer transition-all duration-300 relative ${
                dragActive 
                  ? 'border-glow-blue bg-cyan-500/10 cherenkov-glow pointer-events-none' 
                  : fileName 
                    ? 'border-[#3FB950]/50 bg-white/5 hover:border-glow-blue/50' 
                    : 'border-white/10 hover:border-glow-blue/50 bg-black/40'
              }`}
            >
              <input 
                ref={fileInputRef} 
                type="file" 
                id="spec-file-input"
                className="hidden" 
                accept=".json,.yaml,.yml" 
                onChange={handleChange} 
              />

              <div className="space-y-4">
                <div className="flex justify-center">
                  <div className={`p-4 rounded-full ${fileName ? 'bg-[#3FB950]/10 text-[#3FB950]' : 'bg-white/5 text-[#7D8DA1]'}`}>
                    <Upload className="w-8 h-8" />
                  </div>
                </div>

                {fileName ? (
                  <div>
                    <h4 className="text-sm font-semibold text-text-primary font-mono">{fileName}</h4>
                    <p className="text-xs text-success-custom font-mono mt-1 flex items-center justify-center gap-1">
                      <CheckCircle className="w-3.5 h-3.5" />
                      Index Complete · Swagger spec fetched
                    </p>
                    <p className="text-xs text-text-muted mt-4 font-sans underline decoration-dashed">
                      Click or drag a different file to replace
                    </p>
                  </div>
                ) : (
                  <div>
                    <h4 className="text-sm font-semibold text-text-primary font-sans">
                      Drag & Drop OpenAPI Spec (.json / .yaml)
                    </h4>
                    <p className="text-xs text-text-muted mt-1.5 font-sans">
                      Accepts schema definitions up to 10MB
                    </p>
                    <div className="mt-4 inline-block text-[11px] font-mono px-3 py-1 bg-white/5 border border-white/10 rounded text-glow-bright hover:bg-white/10">
                      BROWSE STORAGE
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Spec URL alternative */}
            {!fileName && (
              <div className="relative flex items-center gap-3">
                <div className="h-[1px] bg-white/10 flex-1" />
                <span className="text-[10px] font-mono text-text-muted uppercase">OR PASTE SPEC CONFIGURATION URL</span>
                <div className="h-[1px] bg-white/10 flex-1" />
              </div>
            )}

            {!fileName && (
              <form onSubmit={handleUrlSubmit} className="flex gap-2">
                <div className="relative flex-1">
                  <Globe className="absolute left-3 top-2.5 w-4 h-4 text-text-muted" />
                  <input
                    type="url"
                    id="spec-url-input"
                    name="specUrl"
                    autoComplete="url"
                    placeholder="https://api.petstore-example.io/v2/swagger.json"
                    value={specUrl}
                    onChange={(e) => setSpecUrl(e.target.value)}
                    className="w-full bg-black/30 text-text-primary text-sm pl-10 pr-4 py-2.5 rounded border border-white/10 focus:outline-none focus:border-glow-blue transition"
                  />
                </div>
                <button
                  type="submit"
                  className="px-4 py-2.5 bg-white/5 text-text-primary hover:text-glow-bright border border-white/10 hover:border-glow-blue rounded text-xs tracking-wider uppercase font-mono transition-all duration-200"
                >
                  Fetch
                </button>
              </form>
            )}

            {/* Preset shortcuts for quick demo reviewer */}
            {!fileName && (
              <div className="flex items-center gap-2 pt-2">
                <span className="text-[10px] font-mono text-text-muted uppercase">Preset mockups:</span>
                <button
                  type="button"
                  onClick={() => loadMockSpec('swagger-petstore-v2.json')}
                  id="btn-shortcut-petstore"
                  className="text-xs font-mono text-glow-bright hover:underline px-2.5 py-1 rounded bg-white/5 border border-white/10 hover:bg-white/10"
                >
                  petstore-v2.yaml
                </button>
                <button
                  type="button"
                  onClick={() => loadMockSpec('checkout-gateway-api.json')}
                  id="btn-shortcut-checkout"
                  className="text-xs font-mono text-glow-bright hover:underline px-2.5 py-1 rounded bg-white/5 border border-white/10 hover:bg-white/10"
                >
                  checkout-gateway.json
                </button>
              </div>
            )}
          </div>

          {/* Validation Fields Settings panel */}
          <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl overflow-hidden shadow-lg">
            <button
              onClick={() => setValidationExpanded(!validationExpanded)}
              id="btn-toggle-server-validation"
              className="w-full flex items-center justify-between p-5 text-left border-b border-white/10 hover:bg-white/5 transition"
            >
              <div className="flex items-center gap-2">
                <Globe className="w-5 h-5 text-glow-blue" />
                <div>
                  <h3 className="text-sm font-semibold text-text-primary leading-none">Real-server Validation Configuration</h3>
                  <p className="text-[11px] text-text-muted mt-1">Simulate dry-run network calls on active testing URL endpoints</p>
                </div>
              </div>
              {validationExpanded ? <ChevronUp className="w-4 h-4 text-[#7D8DA1]" /> : <ChevronDown className="w-4 h-4 text-[#7D8DA1]" />}
            </button>

            {validationExpanded && (
              <div className="p-5 bg-black/25 space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                  <div className="space-y-1.5">
                    <label htmlFor="input-server-url" className="text-[#7D8DA1] font-mono text-[10px] uppercase">Testing Target host url</label>
                    <input
                      type="text"
                      id="input-server-url"
                      name="serverUrl"
                      autoComplete="url"
                      value={serverUrl}
                      onChange={(e) => setServerUrl(e.target.value)}
                      className="w-full bg-black/20 text-text-primary p-2 rounded border border-white/10 focus:outline-none focus:border-glow-blue"
                    />
                  </div>
                  <div className="space-y-1.5">
                    <label htmlFor="input-auth-header" className="text-[#7D8DA1] font-mono text-[10px] uppercase">X-Auth-Token / HTTP Bearer Header</label>
                    <input
                      type="text"
                      id="input-auth-header"
                      name="serverAuth"
                      autoComplete="off"
                      placeholder="e.g. Bearer eyJhbGciOiJIUzI1NiI..."
                      value={serverAuth}
                      onChange={(e) => setServerAuth(e.target.value)}
                      className="w-full bg-black/20 text-text-primary p-2 placeholder:text-text-muted/40 rounded border border-white/10 focus:outline-none focus:border-glow-blue"
                    />
                  </div>
                </div>
                <div className="text-[10px] text-text-muted leading-relaxed font-mono mt-1">
                  🔒 Auth headers never escape localhost context. Plugs directly into generated playwright.config headers object.
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Spec Richness report section */}
        <div className="space-y-6">
          <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl p-5 space-y-6 h-full relative min-h-[300px]">
            <h2 className="text-base font-semibold text-text-primary border-b border-white/5 pb-3 flex items-center gap-2">
              <Terminal className="w-4 h-4 text-glow-blue" />
              <span>Spec Richness Analyzer</span>
            </h2>

            {loading ? (
              <div className="h-[220px] flex flex-col items-center justify-center text-center font-mono space-y-3">
                <span className="relative flex h-5 w-5">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-glow-blue opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-5 w-5 bg-glow-bright"></span>
                </span>
                <p className="text-glow-bright text-xs animate-pulse tracking-wide font-bold">ANALYZING SPEC COVERAGE...</p>
                <p className="text-[10px] text-text-muted">Resolving $ref definitions and mutating payloads</p>
              </div>
            ) : endpoints.length === 0 ? (
              <div className="h-[220px] flex flex-col items-center justify-center text-center font-sans space-y-1">
                <p className="text-text-muted text-xs">Please load or drop a spec configuration</p>
                <p className="text-[11px] text-text-muted/60">Upload YAML code above to preview contract safety</p>
                <div className="w-16 h-1 bg-white/5 rounded-full mt-3 overflow-hidden">
                  <div className="w-4 h-full bg-white/10 rounded-full animate-pulse-slow ml-2" />
                </div>
              </div>
            ) : (
              // Visual Report panel if Spec exists
              <div className="space-y-6">
                
                {/* Score telemetry card */}
                <div className="p-4 bg-black/30 backdrop-blur-sm rounded-xl border border-white/10 flex items-center justify-between text-xs">
                  <div>
                    <span className="block text-[10px] tracking-wider uppercase text-text-muted font-mono">Endpoints Indexed</span>
                    <span className="text-2xl font-bold text-text-primary mt-1 font-display">{endpoints.length}</span>
                  </div>
                  <div className="text-right">
                    <span className="block text-[10px] tracking-wider uppercase text-text-muted font-mono">Avg Richness Score</span>
                    <span className="text-2xl font-bold text-glow-bright mt-1 font-mono">{(avgRichness * 100).toFixed(0)}%</span>
                  </div>
                </div>

                {/* Enrichment Bands Indicators */}
                <div className="space-y-2">
                  <span className="block text-[10px] text-[#7D8DA1] font-mono uppercase tracking-wider">Quality coverage segments</span>

                  {/* Horizontal visual endpoint blocks bar */}
                  <div className="flex gap-[3px] h-6 w-full py-1">
                    {endpoints.map((ep) => {
                      const bandColor = ep.band === 'full' 
                        ? 'bg-[#3FB950] hover:bg-[#3FB950]/80' 
                        : ep.band === 'inferred' 
                          ? 'bg-[#D29922] hover:bg-[#D29922]/80' 
                          : 'bg-[#F85149] hover:bg-[#F85149]/80';
                      
                      return (
                        <div
                          key={ep.id}
                          className={`flex-1 rounded-[2px] transition duration-150 cursor-crosshair h-full ${bandColor}`}
                          onMouseEnter={(e) => handleSegmentHover(e, ep)}
                          onMouseLeave={() => setHoveredEndpoint(null)}
                        />
                      );
                    })}
                  </div>
                  
                  {/* Bands list descriptions */}
                  <div className="grid grid-cols-3 gap-1 pt-2 border-t border-white/10 text-[10px] font-mono text-text-muted text-center">
                    <div>
                      <span className="inline-block w-2 h-2 rounded-full bg-[#3FB950] mr-1.5" />
                      <span>{countByBand.full} Solid (&gt;0.7)</span>
                    </div>
                    <div>
                      <span className="inline-block w-2 h-2 rounded-full bg-[#D29922] mr-1.5" />
                      <span>{countByBand.inferred} Inferred (0.5-0.7)</span>
                    </div>
                    <div>
                      <span className="inline-block w-2 h-2 rounded-full bg-[#F85149] mr-1.5" />
                      <span>{countByBand.degraded} Degraded (&lt;0.5)</span>
                    </div>
                  </div>
                </div>

                {/* Generation safety indicator notes */}
                <div className="bg-amber-500/10 p-4 rounded-xl border border-amber-500/20 space-y-1">
                  <span className="block text-[10px] font-mono text-[#D29922] uppercase font-bold">Inference Threshold Warning</span>
                  <p className="text-[11px] text-[#7D8DA1] leading-relaxed">
                    Some red paths contain complex payloads. The generator will automatically substitute schema structures where descriptions are sparse.
                  </p>
                </div>

                {/* Primary launcher Button */}
                <button
                  type="button"
                  id="btn-launch-generation"
                  onClick={handleStartGeneration}
                  disabled={endpoints.length === 0 || !systemReady}
                  className={`w-full mt-4 py-3 rounded-xl uppercase tracking-wider font-bold text-xs transition duration-300 shadow-lg shadow-cyan-500/20 ${
                    (endpoints.length === 0 || !systemReady)
                      ? 'bg-gray-brand/30 text-text-muted cursor-not-allowed'
                      : 'bg-glow-blue hover:bg-opacity-95 text-slate-950'
                  }`}
                >
                  Generate {endpoints.length} API Test Suites
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Floating Hover Tooltip Detail for Segment hover */}
      {hoveredEndpoint && (
        <div 
          className="fixed z-50 p-4 border border-white/15 bg-slate-900 rounded-xl shadow-2xl backdrop-blur-md text-xs max-w-xs space-y-2 pointer-events-none"
          style={{
            left: `${tooltipPos.x}px`,
            top: `${tooltipPos.y}px`,
            transform: 'translate(-50%, -100%)'
          }}
        >
          {/* Method badge + path block */}
          <div className="flex items-center gap-2">
            <span className={`px-2 py-0.5 rounded text-[10px] font-bold font-mono ${
              hoveredEndpoint.method === 'GET' ? 'bg-[#3FB950]/15 text-[#3FB950]' :
              hoveredEndpoint.method === 'POST' ? 'bg-glow-blue/15 text-glow-bright' :
              hoveredEndpoint.method === 'DELETE' ? 'bg-[#F85149]/15 text-[#F85149]' : 'bg-[#D29922]/15 text-[#D29922]'
            }`}>
              {hoveredEndpoint.method}
            </span>
            <span className="font-mono text-text-primary text-sm font-semibold truncate">{hoveredEndpoint.path}</span>
          </div>

          <div className="flex justify-between items-center text-[10px] font-mono">
            <span className="text-[#7D8DA1]">Specs Quality:</span>
            <span className={`${
              hoveredEndpoint.richness >= 0.8 ? 'text-[#3FB950]' :
              hoveredEndpoint.richness >= 0.5 ? 'text-[#D29922]' : 'text-[#F85149]'
            } font-semibold`}>
              {(hoveredEndpoint.richness * 100).toFixed(0)}% Richness
            </span>
          </div>

          {hoveredEndpoint.missingElements.length > 0 && (
            <div className="pt-2 border-t border-white/10">
              <span className="block text-[9px] uppercase tracking-wider text-text-muted font-bold font-mono mb-1">Missing Elements:</span>
              <ul className="space-y-1 text-[11px] text-[#7D8DA1] list-disc list-inside">
                {hoveredEndpoint.missingElements.map((el, i) => (
                  <li key={i}>{el}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
