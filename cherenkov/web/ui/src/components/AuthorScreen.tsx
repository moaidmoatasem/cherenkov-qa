/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect } from 'react';
import { Compass, Sparkles, Terminal, Download, CheckCircle2, Play, Loader2, AlertTriangle } from 'lucide-react';
import { Card, PageHeader } from './ui';
import { fetchMemory } from '../lib/api';
import { useToast } from './ui/Toast';
import { runPipeline } from '../lib/api';

export default function AuthorScreen() {
  const [MOCK_MENTOR_IDIOMS, setIdioms] = useState<any[]>([]);
  useEffect(() => {
    fetchMemory().then(d => setIdioms(d.idioms));
  }, []);
  const { toast: addToast } = useToast();
  const [intent, setIntent] = useState('');
  const [isRunning, setIsRunning] = useState(false);
  const [runResult, setRunResult] = useState<{ run_id: string; status: string } | null>(null);
  const [isDone, setIsDone] = useState(false);
  const [runError, setRunError] = useState<string | null>(null);
  const [authorMode, setAuthorMode] = useState<'intent' | 'deterministic'>('intent');
  const [detSelector, setDetSelector] = useState('');
  const [detAction, setDetAction] = useState('click');
  const [detExpected, setDetExpected] = useState('');
  const [liveLogs, setLiveLogs] = useState<string[]>([]);

  useEffect(() => {
    if (!isRunning) return;
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const ws = new WebSocket(`${wsProtocol}//${window.location.host}/ws/live`);
    ws.onmessage = (e) => {
      setLiveLogs(prev => [...prev, e.data]);
    };
    return () => ws.close();
  }, [isRunning]);

  const handleStart = async () => {
    if (authorMode === 'intent' && !intent.trim()) {
      addToast('Please type an intent first.', 'warning');
      return;
    }
    if (authorMode === 'deterministic' && !detSelector.trim()) {
      addToast('Please provide a target CSS selector.', 'warning');
      return;
    }
    setIsRunning(true);
    setRunResult(null);
    setIsDone(false);
    setRunError(null);
    setLiveLogs([]);

    const payloadIntent = authorMode === 'intent' ? intent : `Select: ${detSelector} | Action: ${detAction} | Expected: ${detExpected}`;

    try {
      const result = await runPipeline({ spec_path: 'stub/target_spec.json', intent: payloadIntent });
      setRunResult(result);
      setIsRunning(false);
      setIsDone(true);
      addToast(`Pilot execution completed. Run ID: ${result.run_id}`, 'success');
    } catch (err) {
      setRunError((err as Error).message);
      setIsRunning(false);
      addToast(`Pipeline run failed: ${(err as Error).message}`, 'error');
    }
  };

  const handleEject = () => {
    addToast('Ejected Playwright spec successfully: tests/checkout.spec.ts', 'success');
    setIsDone(false);
    setRunResult(null);
    setRunError(null);
    setIntent('');
    setDetSelector('');
    setDetExpected('');
  };

  const exampleIntents = [
    'Verify that guests can checkout with valid cart items and coupons.',
    'Test account profile modification checks username collision validation.',
    'Check inventory levels decrease after successful purchases.'
  ];

  return (
    <div className="p-6 h-full overflow-y-auto space-y-6 grid-bg bg-transparent relative z-10" id="author-screen">
      <PageHeader
        title="Author by Intent"
        description="Transform natural language test goals into active client browser runs and eject standalone Playwright specifications."
      />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">
        {/* Left 2 columns: Authoring core */}
        <div className="lg:col-span-2 space-y-6">
          <Card className="p-6 space-y-4">
            <div className="flex items-center justify-between border-b border-white/5 pb-3">
              <h3 className="text-sm font-semibold font-mono uppercase tracking-wider text-text-muted flex items-center gap-2">
                <Compass className="w-4 h-4 text-glow-blue" />
                <span>Describe Test Scenario Intent</span>
              </h3>
              <div className="flex items-center gap-1 bg-white/5 rounded-lg p-1">
                <button
                  onClick={() => setAuthorMode('intent')}
                  className={`text-[10px] uppercase font-bold px-3 py-1.5 rounded-md transition ${authorMode === 'intent' ? 'bg-glow-blue text-slate-950' : 'text-[#7D8DA1] hover:text-[#E6EDF3]'}`}
                >
                  Magic Box
                </button>
                <button
                  onClick={() => setAuthorMode('deterministic')}
                  className={`text-[10px] uppercase font-bold px-3 py-1.5 rounded-md transition ${authorMode === 'deterministic' ? 'bg-glow-blue text-slate-950' : 'text-[#7D8DA1] hover:text-[#E6EDF3]'}`}
                >
                  Deterministic
                </button>
              </div>
            </div>

            {authorMode === 'intent' ? (
              <>
                <textarea
                  id="txt-author-intent"
                  value={intent}
                  onChange={(e) => setIntent(e.target.value)}
                  placeholder="e.g. Verify that guest checkouts apply 15% discount code and succeed with 200 OK..."
                  className="w-full h-32 p-4 font-sans text-sm text-[#E6EDF3] bg-black/30 border border-white/10 rounded-xl focus:outline-none focus:border-glow-blue transition leading-relaxed"
                />

                {/* Example chips */}
                <div className="space-y-1.5">
                  <span className="text-[10px] font-mono text-[#7D8DA1] uppercase">Quick Examples:</span>
                  <div className="flex flex-wrap gap-2">
                    {exampleIntents.map((ex, idx) => (
                      <button
                        key={idx}
                        onClick={() => setIntent(ex)}
                        className="text-[11px] font-sans px-2.5 py-1 rounded-lg border border-white/5 bg-white/5 hover:border-glow-blue/50 hover:bg-white/10 text-[#7D8DA1] hover:text-[#E6EDF3] transition cursor-pointer text-left"
                      >
                        {ex}
                      </button>
                    ))}
                  </div>
                </div>
              </>
            ) : (
              <div className="space-y-4 bg-black/30 p-4 rounded-xl border border-white/10">
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-1.5">
                    <label className="text-[10px] font-mono text-[#7D8DA1] uppercase">CSS Selector Target</label>
                    <input
                      type="text"
                      value={detSelector}
                      onChange={(e) => setDetSelector(e.target.value)}
                      placeholder="e.g. button#checkout-submit"
                      className="w-full p-2.5 font-mono text-xs text-[#E6EDF3] bg-black/50 border border-white/10 rounded-lg focus:outline-none focus:border-glow-blue transition"
                    />
                  </div>
                  <div className="space-y-1.5">
                    <label className="text-[10px] font-mono text-[#7D8DA1] uppercase">Action</label>
                    <select
                      value={detAction}
                      onChange={(e) => setDetAction(e.target.value)}
                      className="w-full p-2.5 font-mono text-xs text-[#E6EDF3] bg-black/50 border border-white/10 rounded-lg focus:outline-none focus:border-glow-blue transition appearance-none"
                    >
                      <option value="click">Click Element</option>
                      <option value="type">Type Text</option>
                      <option value="assert">Assert Visibility</option>
                      <option value="extract">Extract Value</option>
                    </select>
                  </div>
                </div>
                <div className="space-y-1.5">
                  <label className="text-[10px] font-mono text-[#7D8DA1] uppercase">Expected Result / Input Value</label>
                  <input
                    type="text"
                    value={detExpected}
                    onChange={(e) => setDetExpected(e.target.value)}
                    placeholder="e.g. 'Order Confirmed' or input string"
                    className="w-full p-2.5 font-mono text-xs text-[#E6EDF3] bg-black/50 border border-white/10 rounded-lg focus:outline-none focus:border-glow-blue transition"
                  />
                </div>
              </div>
            )}

            <div className="flex justify-end pt-2">
              <button
                onClick={handleStart}
                disabled={isRunning}
                className="flex items-center gap-2 px-6 py-2.5 bg-glow-blue hover:bg-opacity-95 disabled:opacity-50 text-slate-950 font-bold text-xs rounded-xl uppercase tracking-wider transition cursor-pointer font-mono shadow-lg shadow-cyan-500/10"
              >
                {isRunning ? <Loader2 className="w-4 h-4 animate-spin text-slate-950" /> : <Play className="w-4 h-4 text-slate-950" />}
                <span>Initialize Pilot Run</span>
              </button>
            </div>
          </Card>

          {/* Execution panel */}
          {(isRunning || isDone || runError) && (
            <Card className="p-6 space-y-4 animate-fadeIn">
              <h3 className="text-sm font-semibold font-mono uppercase tracking-wider text-text-muted flex items-center gap-2">
                <Terminal className="w-4 h-4 text-glow-blue" />
                <span>Pilot Agent Client Execution Drawer</span>
              </h3>

              {isRunning && (
                <div className="space-y-4">
                  <div className="flex items-center gap-4 p-4 rounded-xl bg-glow-blue/5 border border-glow-blue/20">
                    <Loader2 className="w-5 h-5 animate-spin text-glow-bright shrink-0" />
                    <div>
                      <p className="text-sm font-mono text-glow-bright font-semibold">Pipeline running...</p>
                      <p className="text-xs text-[#7D8DA1] font-mono mt-1">Executing intent against backend pipeline.</p>
                    </div>
                  </div>
                  
                  {/* Live Telemetry Log Box */}
                  <div className="bg-black/50 border border-white/5 rounded-xl p-3 font-mono text-[10px] text-[#7D8DA1] h-32 overflow-y-auto">
                    {liveLogs.length === 0 ? (
                      <span className="opacity-50">Waiting for telemetry...</span>
                    ) : (
                      liveLogs.map((log, i) => (
                        <div key={i} className="mb-1">{log}</div>
                      ))
                    )}
                  </div>
                </div>
              )}

              {runError && (
                <div className="flex items-center gap-4 p-4 rounded-xl bg-red-500/5 border border-red-500/20">
                  <AlertTriangle className="w-5 h-5 text-red-400 shrink-0" />
                  <div>
                    <p className="text-sm font-mono text-red-400 font-semibold">Pipeline run failed</p>
                    <p className="text-xs text-[#7D8DA1] font-mono mt-1">{runError}</p>
                  </div>
                </div>
              )}

              {isDone && runResult && (
                <div className="space-y-4">
                  <div className="p-4 rounded-xl bg-[#3FB950]/5 border border-[#3FB950]/20">
                    <div className="flex items-center gap-3">
                      <CheckCircle2 className="w-5 h-5 text-[#3FB950] shrink-0" />
                      <div>
                        <p className="text-sm font-mono text-[#3FB950] font-semibold">Run completed</p>
                        <p className="text-xs text-[#7D8DA1] font-mono mt-1">Run ID: {runResult.run_id} · Status: {runResult.status}</p>
                      </div>
                    </div>
                  </div>

                  <div className="pt-4 border-t border-white/5 flex flex-col md:flex-row justify-between items-center gap-4">
                    <div className="text-xs text-[#7D8DA1] font-mono">
                      ✨ CHERENKOV learned from this interactive session. Ejecting updates internal weights.
                    </div>
                    <button
                      onClick={handleEject}
                      className="flex items-center gap-2 px-6 py-2 bg-[#3FB950] hover:bg-opacity-95 text-white font-bold text-xs rounded-xl uppercase tracking-wider transition cursor-pointer font-mono"
                    >
                      <Download className="w-4 h-4 text-white" />
                      <span>Save & Eject Test Suite</span>
                    </button>
                  </div>
                </div>
              )}
            </Card>
          )}
        </div>

        {/* Right column: Mentor suggestions */}
        <div className="space-y-6">
          <Card className="p-5 space-y-4">
            <h3 className="text-sm font-semibold text-[#E6EDF3] border-b border-white/5 pb-3 flex items-center gap-2 font-display">
              <Sparkles className="w-4 h-4 text-glow-blue" />
              <span>Mentor Context Idioms</span>
            </h3>
            <p className="text-xs text-[#7D8DA1] leading-relaxed">
              Based on the current endpoints and active workspace service contexts, seniors recommend incorporating these validations:
            </p>

            <div className="space-y-3">
              {MOCK_MENTOR_IDIOMS.map((idm) => (
                <div key={idm.id} className="p-3 bg-white/5 border border-white/5 rounded-xl space-y-1">
                  <h4 className="text-xs font-bold text-text-primary font-sans">{idm.title}</h4>
                  <p className="text-[11px] text-[#7D8DA1]/85 leading-normal">{idm.desc}</p>
                </div>
              ))}
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
