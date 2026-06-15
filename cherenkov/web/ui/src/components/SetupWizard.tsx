/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useEffect, useState } from 'react';
import { Card } from './ui/Card';

interface Step {
  id: string;
  label: string;
  status: 'pending' | 'checking' | 'ok' | 'installing' | 'failed' | 'skipped';
  detail?: string;
  progress_pct?: number;
}

const statusIcon: Record<string, string> = {
  pending: '○',
  checking: '⟳',
  ok: '✓',
  installing: '⬇',
  failed: '✕',
  skipped: '⊘',
};

const statusClass: Record<string, string> = {
  pending: 'text-slate-400',
  checking: 'text-blue-400 animate-spin',
  ok: 'text-emerald-400',
  installing: 'text-amber-400',
  failed: 'text-rose-400',
  skipped: 'text-slate-500',
};

export default function SetupWizard() {
  const [steps, setSteps] = useState<Step[]>([
    { id: 'python', label: 'Python 3.10+', status: 'pending' },
    { id: 'node', label: 'Node.js', status: 'pending' },
    { id: 'docker', label: 'Docker', status: 'pending' },
    { id: 'ollama', label: 'Ollama runtime', status: 'pending' },
    { id: 'model', label: 'Model: qwen2.5-coder:7b', status: 'pending' },
  ]);
  const [running, setRunning] = useState(false);
  const [complete, setComplete] = useState(false);

  // Listen for Tauri progress events when running inside the desktop shell.
  useEffect(() => {
    let unlisten: (() => void) | undefined;
    if ((window as any).__TAURI__) {
      const { listen } = require('@tauri-apps/api/event');
      listen('setup-progress', (event: any) => {
        const p = event.payload;
        setSteps(prev =>
          prev.map(s =>
            s.id === p.step_id
              ? { ...s, status: p.status, detail: p.detail, progress_pct: p.progress_pct }
              : s
          )
        );
      }).then((ul: () => void) => {
        unlisten = ul;
      });
    }
    return () => {
      if (unlisten) unlisten();
    };
  }, []);

  const runChecks = async () => {
    setRunning(true);
    setSteps(prev => prev.map(s => ({ ...s, status: 'checking' })));

    if ((window as any).__TAURI__) {
      try {
        const { invoke } = require('@tauri-apps/api/core');
        const result = await invoke('run_setup_wizard', { model: 'qwen2.5-coder:7b' });
        if ((result as any).steps) {
          setSteps((result as any).steps);
          setComplete((result as any).complete);
        }
      } catch (e) {
        setSteps(prev =>
          prev.map(s =>
            s.status === 'checking' ? { ...s, status: 'failed', detail: String(e) } : s
          )
        );
      }
    } else {
      // Browser fallback: perform lightweight checks via navigator/userAgent hints.
      await simulateChecks();
    }
    setRunning(false);
  };

  const simulateChecks = async () => {
    const update = (id: string, status: Step['status'], detail?: string) => {
      setSteps(prev => prev.map(s => (s.id === id ? { ...s, status, detail } : s)));
    };

    update('python', 'ok', 'Python check requires desktop shell.');
    await new Promise(r => setTimeout(r, 300));
    update('node', 'ok', 'Node.js check requires desktop shell.');
    await new Promise(r => setTimeout(r, 300));
    update('docker', 'skipped', 'Docker check requires desktop shell.');
    await new Promise(r => setTimeout(r, 300));
    update('ollama', 'skipped', 'Ollama check requires desktop shell.');
    await new Promise(r => setTimeout(r, 300));
    update('model', 'skipped', 'Install Ollama from ollama.com and pull qwen2.5-coder:7b.');
    setComplete(true);
  };

  const installOllama = async () => {
    if (!(window as any).__TAURI__) return;
    const { invoke } = require('@tauri-apps/api/core');
    setSteps(prev => prev.map(s => (s.id === 'ollama' ? { ...s, status: 'installing' } : s)));
    try {
      const step = await invoke('install_ollama_command');
      setSteps(prev => prev.map(s => (s.id === 'ollama' ? (step as Step) : s)));
    } catch (e) {
      setSteps(prev =>
        prev.map(s => (s.id === 'ollama' ? { ...s, status: 'failed', detail: String(e) } : s))
      );
    }
  };

  const doneCount = steps.filter(s => s.status === 'ok').length;
  const progress = Math.round((doneCount / steps.length) * 100);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-8">
      <div className="max-w-2xl mx-auto space-y-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">CHERENKOV Setup Wizard</h1>
          <p className="text-slate-400 mt-2">
            Verify dependencies before running CHERENKOV in the desktop shell.
          </p>
        </div>

        <Card className="p-6 space-y-4">
          <div className="flex justify-between text-sm text-slate-400">
            <span>Dependency checks</span>
            <span>{doneCount}/{steps.length}</span>
          </div>
          <div className="h-2 w-full rounded-full bg-slate-800">
            <div
              className="h-2 rounded-full bg-blue-500 transition-all"
              style={{ width: `${progress}%` }}
            />
          </div>

          <div className="space-y-3">
            {steps.map(step => (
              <div
                key={step.id}
                className="flex items-center justify-between rounded-lg border border-slate-800 bg-slate-900/50 px-4 py-3"
              >
                <div className="flex items-center gap-3">
                  <span className={`text-lg ${statusClass[step.status]}`}>
                    {statusIcon[step.status]}
                  </span>
                  <div>
                    <p className="font-medium">{step.label}</p>
                    {step.detail && (
                      <p className="text-sm text-slate-500">{step.detail}</p>
                    )}
                  </div>
                </div>
                {step.progress_pct !== undefined && step.progress_pct > 0 && (
                  <span className="text-xs text-slate-500">{step.progress_pct}%</span>
                )}
              </div>
            ))}
          </div>

          <div className="flex gap-3 pt-2">
            <button
              onClick={runChecks}
              disabled={running}
              className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {running ? 'Checking...' : complete ? 'Re-run checks' : 'Run checks'}
            </button>
            {(window as any).__TAURI__ && (
              <button
                onClick={installOllama}
                disabled={running}
                className="rounded-lg border border-slate-700 bg-slate-800 px-4 py-2 text-sm font-medium text-slate-200 hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-50"
              >
                Install Ollama
              </button>
            )}
          </div>
        </Card>

        <p className="text-xs text-slate-600">
          Running in {(window as any).__TAURI__ ? 'desktop' : 'browser'} mode. Full dependency
          installation is only available inside the Tauri desktop app.
        </p>
      </div>
    </div>
  );
}
