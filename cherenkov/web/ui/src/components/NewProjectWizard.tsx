import React, { useState, useRef } from 'react';
import {
  X, FolderGit2, Globe, Upload, GitBranch, FolderOpen,
  ArrowRight, ArrowLeft, CheckCircle2, Loader2, Sparkles, FileCode2
} from 'lucide-react';
import { ingestSpec, createProject } from '../lib/api';
import { useToast } from './ui/Toast';

interface Props {
  onClose: () => void;
  onCreated: (project: any, specPath: string) => void;
}

const STEPS = [
  { id: 'name',  label: 'Project',    desc: 'Name your project & set target URL' },
  { id: 'spec',  label: 'Spec / SDD', desc: 'Upload your API spec or design doc' },
  { id: 'repo',  label: 'Repository', desc: 'New scaffold or existing repo?' },
];

export default function NewProjectWizard({ onClose, onCreated }: Props) {
  const { toast } = useToast();
  const [step, setStep] = useState(0);

  // Step 1
  const [name, setName] = useState('');
  const [targetUrl, setTargetUrl] = useState('');

  // Step 2
  const [specFile, setSpecFile] = useState<File | null>(null);
  const [specUrl, setSpecUrl] = useState('');
  const [dragActive, setDragActive] = useState(false);
  const [ingestLoading, setIngestLoading] = useState(false);
  const [ingestResult, setIngestResult] = useState<{ spec_path: string; endpoints: any[]; richness: number } | null>(null);
  const [ingestError, setIngestError] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  // Step 3
  const [repoType, setRepoType] = useState<'new' | 'existing'>('new');
  const [repoPath, setRepoPath] = useState('');

  // Submit
  const [creating, setCreating] = useState(false);

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragActive(false);
    const file = e.dataTransfer.files[0];
    if (file) { setSpecFile(file); setSpecUrl(''); }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) { setSpecFile(file); setSpecUrl(''); }
  };

  const handleIngest = async () => {
    if (!specFile && !specUrl) { toast('Provide a spec file or URL', 'warning'); return; }
    setIngestLoading(true);
    setIngestError(null);
    try {
      const data = await ingestSpec(specFile, specUrl || null);
      setIngestResult(data);
      toast(`Spec parsed — ${data.endpoints.length} endpoint(s) found`, 'success');
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Ingestion failed';
      setIngestError(msg);
      toast(msg, 'error');
    } finally {
      setIngestLoading(false);
    }
  };

  const canNext = [
    name.trim().length > 0,
    ingestResult !== null || (!specFile && !specUrl), // spec optional
    true,
  ][step];

  const handleNext = async () => {
    if (step === 1 && (specFile || specUrl) && !ingestResult) {
      await handleIngest();
      return;
    }
    if (step < STEPS.length - 1) { setStep(s => s + 1); return; }
    // Final submit
    setCreating(true);
    try {
      const project = await createProject({
        name: name.trim(),
        target_url: targetUrl.trim(),
        spec_path: ingestResult?.spec_path || '',
        repo_type: repoType,
        repo_path: repoPath.trim(),
      });
      toast(`Project "${name}" created!`, 'success');
      onCreated(project, ingestResult?.spec_path || '');
    } catch (err) {
      toast('Failed to create project', 'error');
    } finally {
      setCreating(false);
    }
  };

  const stepLabel = step === 1 && (specFile || specUrl) && !ingestResult
    ? 'Parse Spec'
    : step === STEPS.length - 1
    ? 'Create Project'
    : 'Next';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm">
      <div className="w-full max-w-xl bg-[#0d1117] border border-white/10 rounded-2xl shadow-2xl overflow-hidden">

        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-white/10">
          <div className="flex items-center gap-3">
            <FolderGit2 className="w-5 h-5 text-[#22d3ee]" />
            <h2 className="text-sm font-semibold text-white">New Project</h2>
          </div>
          <button onClick={onClose} className="text-white/40 hover:text-white transition">
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Step progress */}
        <div className="flex items-center px-6 py-3 border-b border-white/5 gap-0">
          {STEPS.map((s, i) => (
            <React.Fragment key={s.id}>
              <div className="flex items-center gap-2">
                <div className={`w-6 h-6 rounded-full flex items-center justify-center text-[11px] font-bold transition-all ${
                  i < step ? 'bg-emerald-500 text-white' :
                  i === step ? 'bg-[#22d3ee] text-black' :
                  'bg-white/10 text-white/40'
                }`}>
                  {i < step ? <CheckCircle2 className="w-3.5 h-3.5" /> : i + 1}
                </div>
                <span className={`text-xs font-medium ${i === step ? 'text-white' : i < step ? 'text-emerald-400' : 'text-white/40'}`}>
                  {s.label}
                </span>
              </div>
              {i < STEPS.length - 1 && (
                <div className={`flex-1 h-px mx-3 ${i < step ? 'bg-emerald-500/50' : 'bg-white/10'}`} />
              )}
            </React.Fragment>
          ))}
        </div>

        {/* Body */}
        <div className="px-6 py-6 min-h-[280px]">

          {/* Step 0 — Name + URL */}
          {step === 0 && (
            <div className="space-y-4">
              <p className="text-xs text-white/50">Give your project a name and point it at the API you want to test.</p>
              <div>
                <label className="text-xs font-medium text-white/70 block mb-1.5">Project name *</label>
                <input
                  autoFocus
                  value={name}
                  onChange={e => setName(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && canNext && handleNext()}
                  placeholder="e.g. Payments API, Checkout Service…"
                  className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2.5 text-sm text-white placeholder:text-white/30 focus:outline-none focus:border-[#22d3ee] transition"
                />
              </div>
              <div>
                <label className="text-xs font-medium text-white/70 block mb-1.5">
                  Target API URL <span className="text-white/30">(optional — can be set later)</span>
                </label>
                <div className="relative">
                  <Globe className="absolute left-3 top-2.5 w-4 h-4 text-white/30" />
                  <input
                    value={targetUrl}
                    onChange={e => setTargetUrl(e.target.value)}
                    placeholder="https://api.example.com/v1"
                    className="w-full bg-white/5 border border-white/10 rounded-lg pl-9 pr-3 py-2.5 text-sm text-white placeholder:text-white/30 focus:outline-none focus:border-[#22d3ee] transition"
                  />
                </div>
              </div>
              <div className="bg-[#22d3ee]/5 border border-[#22d3ee]/20 rounded-lg p-3 text-xs text-[#22d3ee]/80">
                <Sparkles className="w-3.5 h-3.5 inline mr-1.5 mb-0.5" />
                CHERENKOV will parse your spec, generate test cases, and scaffold a Playwright suite — no automation knowledge required.
              </div>
            </div>
          )}

          {/* Step 1 — Spec / SDD upload */}
          {step === 1 && (
            <div className="space-y-4">
              <p className="text-xs text-white/50">
                Upload your OpenAPI spec, Swagger file, or any SDD document.
                <span className="text-white/30"> Skip this step if you'll paste a URL instead.</span>
              </p>

              {/* Drag-drop zone */}
              {!ingestResult && (
                <div
                  onDragEnter={e => { e.preventDefault(); setDragActive(true); }}
                  onDragOver={e => { e.preventDefault(); setDragActive(true); }}
                  onDragLeave={e => { e.preventDefault(); setDragActive(false); }}
                  onDrop={handleDrop}
                  onClick={() => fileRef.current?.click()}
                  className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all ${
                    dragActive ? 'border-[#22d3ee] bg-[#22d3ee]/10' : 'border-white/10 hover:border-white/30 bg-white/2'
                  }`}
                >
                  <input ref={fileRef} type="file" accept=".json,.yaml,.yml" className="hidden" onChange={handleFileChange} />
                  <Upload className="w-8 h-8 text-white/30 mx-auto mb-2" />
                  {specFile ? (
                    <p className="text-sm text-[#22d3ee] font-medium">{specFile.name}</p>
                  ) : (
                    <>
                      <p className="text-sm text-white/60">Drag & drop <span className="text-white/90">.json / .yaml</span> here</p>
                      <p className="text-xs text-white/30 mt-1">or click to browse</p>
                    </>
                  )}
                </div>
              )}

              {/* URL fallback */}
              {!specFile && !ingestResult && (
                <div>
                  <p className="text-[11px] text-white/40 mb-1.5 text-center">— or paste a spec URL —</p>
                  <div className="relative">
                    <Globe className="absolute left-3 top-2.5 w-4 h-4 text-white/30" />
                    <input
                      value={specUrl}
                      onChange={e => setSpecUrl(e.target.value)}
                      placeholder="https://petstore3.swagger.io/api/v3/openapi.json"
                      className="w-full bg-white/5 border border-white/10 rounded-lg pl-9 pr-3 py-2.5 text-sm text-white placeholder:text-white/30 focus:outline-none focus:border-[#22d3ee] transition"
                    />
                  </div>
                </div>
              )}

              {/* Ingest result */}
              {ingestResult && (
                <div className="bg-emerald-500/10 border border-emerald-500/30 rounded-xl p-4 space-y-2">
                  <div className="flex items-center gap-2 text-emerald-400 text-sm font-medium">
                    <CheckCircle2 className="w-4 h-4" />
                    Spec parsed successfully
                  </div>
                  <div className="grid grid-cols-2 gap-2 text-xs text-white/60">
                    <span>{ingestResult.endpoints.length} endpoints discovered</span>
                    <span>Avg richness: {Math.round(ingestResult.richness * 100)}%</span>
                  </div>
                  <div className="flex flex-wrap gap-1.5 mt-1">
                    {ingestResult.endpoints.slice(0, 8).map((ep, i) => (
                      <span key={i} className="text-[10px] px-2 py-0.5 bg-white/5 border border-white/10 rounded font-mono text-white/60">
                        {ep.method} {ep.path}
                      </span>
                    ))}
                    {ingestResult.endpoints.length > 8 && (
                      <span className="text-[10px] px-2 py-0.5 text-white/30">+{ingestResult.endpoints.length - 8} more</span>
                    )}
                  </div>
                  <button onClick={() => { setIngestResult(null); setSpecFile(null); setSpecUrl(''); }}
                    className="text-xs text-white/30 hover:text-white/60 transition mt-1">
                    ← Use a different spec
                  </button>
                </div>
              )}

              {ingestError && (
                <p className="text-xs text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-2">{ingestError}</p>
              )}

              <p className="text-xs text-white/30 text-center">
                <FileCode2 className="w-3 h-3 inline mr-1" />
                No spec yet? Skip — you can add one after creating the project.
              </p>
            </div>
          )}

          {/* Step 2 — Repo type */}
          {step === 2 && (
            <div className="space-y-4">
              <p className="text-xs text-white/50">Where should CHERENKOV put the generated Playwright tests?</p>

              <div className="grid grid-cols-2 gap-3">
                <button
                  onClick={() => setRepoType('new')}
                  className={`p-4 rounded-xl border-2 text-left transition-all ${
                    repoType === 'new'
                      ? 'border-[#22d3ee] bg-[#22d3ee]/10'
                      : 'border-white/10 hover:border-white/30 bg-white/2'
                  }`}
                >
                  <Sparkles className={`w-5 h-5 mb-2 ${repoType === 'new' ? 'text-[#22d3ee]' : 'text-white/40'}`} />
                  <p className={`text-sm font-semibold ${repoType === 'new' ? 'text-[#22d3ee]' : 'text-white/70'}`}>
                    New repo
                  </p>
                  <p className="text-xs text-white/40 mt-1">
                    Scaffold a fresh Playwright project for me
                  </p>
                </button>

                <button
                  onClick={() => setRepoType('existing')}
                  className={`p-4 rounded-xl border-2 text-left transition-all ${
                    repoType === 'existing'
                      ? 'border-[#22d3ee] bg-[#22d3ee]/10'
                      : 'border-white/10 hover:border-white/30 bg-white/2'
                  }`}
                >
                  <FolderOpen className={`w-5 h-5 mb-2 ${repoType === 'existing' ? 'text-[#22d3ee]' : 'text-white/40'}`} />
                  <p className={`text-sm font-semibold ${repoType === 'existing' ? 'text-[#22d3ee]' : 'text-white/70'}`}>
                    Existing repo
                  </p>
                  <p className="text-xs text-white/40 mt-1">
                    I already have an automation project
                  </p>
                </button>
              </div>

              {repoType === 'existing' && (
                <div>
                  <label className="text-xs font-medium text-white/70 block mb-1.5">Repo path</label>
                  <div className="relative">
                    <GitBranch className="absolute left-3 top-2.5 w-4 h-4 text-white/30" />
                    <input
                      value={repoPath}
                      onChange={e => setRepoPath(e.target.value)}
                      placeholder="/home/you/my-tests or https://github.com/org/repo"
                      className="w-full bg-white/5 border border-white/10 rounded-lg pl-9 pr-3 py-2.5 text-sm text-white placeholder:text-white/30 focus:outline-none focus:border-[#22d3ee] transition"
                    />
                  </div>
                </div>
              )}

              {repoType === 'new' && (
                <div className="bg-[#22d3ee]/5 border border-[#22d3ee]/20 rounded-lg p-3 text-xs text-[#22d3ee]/80">
                  <CheckCircle2 className="w-3.5 h-3.5 inline mr-1.5 mb-0.5" />
                  CHERENKOV will generate a ready-to-run <span className="font-mono">playwright.config.ts</span> + test files in <span className="font-mono">./eject/{name.trim() || 'project'}/</span>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-white/10 bg-white/2">
          <button
            onClick={() => step > 0 ? setStep(s => s - 1) : onClose()}
            className="flex items-center gap-1.5 text-sm text-white/50 hover:text-white transition"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            {step > 0 ? 'Back' : 'Cancel'}
          </button>

          <div className="flex items-center gap-3">
            {step === 1 && !ingestResult && !specFile && !specUrl && (
              <button onClick={() => setStep(2)} className="text-xs text-white/40 hover:text-white/70 transition">
                Skip spec →
              </button>
            )}
            <button
              onClick={handleNext}
              disabled={!canNext || ingestLoading || creating}
              className="flex items-center gap-2 px-5 py-2 rounded-lg bg-[#22d3ee] text-black text-sm font-semibold disabled:opacity-40 disabled:cursor-not-allowed hover:bg-[#67e8f9] transition"
            >
              {(ingestLoading || creating) && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
              {stepLabel}
              {!ingestLoading && !creating && <ArrowRight className="w-3.5 h-3.5" />}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
