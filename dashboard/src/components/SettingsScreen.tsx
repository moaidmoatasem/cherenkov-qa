/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState } from 'react';
import { 
  Settings, 
  Cpu, 
  KeyRound, 
  SlidersHorizontal, 
  CheckCircle,
  Database,
  Shield,
  Activity
} from 'lucide-react';
import CherenkovLogo from './CherenkovLogo';

export default function SettingsScreen() {
  const [model, setModel] = useState('qwen-coder');
  const [threadLimit, setThreadLimit] = useState(4);
  const [logDensity, setLogDensity] = useState('verbose');
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [apiSecret, setApiSecret] = useState('');

  const handleSave = () => {
    setSaveSuccess(true);
    setTimeout(() => setSaveSuccess(false), 2000);
  };

  return (
    <div className="p-6 h-full overflow-y-auto space-y-6 grid-bg bg-transparent relative z-10" id="settings-screen">
      
      {/* Title */}
      <div className="flex items-center gap-4">
        <CherenkovLogo variant="icon" size={42} />
        <div>
          <h1 className="font-display font-bold text-3xl text-text-primary tracking-tight">
            System Settings & Credentials
          </h1>
          <p className="text-sm text-text-muted mt-1 leading-relaxed">
            Configure the underlying Ollama local runners, prompt budgets, and API telemetry relays.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start max-w-5xl">
        {/* Forms column */}
        <div className="lg:col-span-2 space-y-6">
          <div className="bg-white/5 backdrop-blur-xl border border-white/10 p-6 rounded-2xl space-y-6">
            
            {/* Model Provider Section */}
            <div className="space-y-4">
              <h2 className="text-sm font-semibold font-mono uppercase tracking-wider text-text-muted flex items-center gap-2">
                <Cpu className="w-4 h-4 text-glow-blue" />
                <span>Synthetic Synthesis Model Provider</span>
              </h2>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                {/* local option */}
                <div 
                  onClick={() => setModel('qwen-coder')}
                  className={`p-4 rounded-xl border transition cursor-pointer flex flex-col justify-between ${
                    model === 'qwen-coder'
                      ? 'bg-white/10 border-glow-blue shadow-lg shadow-cyan-500/5'
                      : 'bg-black/20 border-white/5 hover:border-text-muted'
                  }`}
                >
                  <div>
                    <span className="block font-sans font-bold text-text-primary text-sm">Qwen 2.5 Coder (7B)</span>
                    <span className="block text-[10px] text-[#7D8DA1] mt-1 font-mono">Local execution · Ollama integration</span>
                  </div>
                  <span className="text-[9px] font-mono text-glow-bright mt-3 block">0% API COST PROJECTIONS</span>
                </div>

                {/* Gemini flash option */}
                <div 
                  onClick={() => setModel('gemini-flash')}
                  className={`p-4 rounded-xl border transition cursor-pointer flex flex-col justify-between ${
                    model === 'gemini-flash'
                      ? 'bg-white/10 border-glow-blue shadow-lg shadow-cyan-500/5'
                      : 'bg-black/20 border-white/5 hover:border-text-muted'
                  }`}
                >
                  <div>
                    <span className="block font-sans font-bold text-text-primary text-sm">Gemini 2.5 Flash</span>
                    <span className="block text-[10px] text-[#7D8DA1] mt-1 font-mono">Cloud execution · Serverless token endpoints</span>
                  </div>
                  <span className="text-[9px] font-mono text-glow-bright mt-3 block">HIGH COVERAGE DISPATCHER</span>
                </div>
              </div>
            </div>

            {/* Prompt Budgets Slider */}
            <div className="space-y-4 pt-4 border-t border-white/5">
              <h2 className="text-sm font-semibold font-mono uppercase tracking-wider text-text-muted flex items-center gap-2">
                <SlidersHorizontal className="w-4 h-4 text-glow-blue" />
                <span>Parallelization Thread Limit</span>
              </h2>

              <div className="space-y-3">
                <div className="flex justify-between items-center text-xs font-mono text-[#E6EDF3]">
                  <span>MAX INSTANCES:</span>
                  <span className="text-glow-bright font-bold">{threadLimit} THREADS</span>
                </div>
                <input
                  type="range"
                  min="1"
                  max="8"
                  value={threadLimit}
                  onChange={(e) => setThreadLimit(Number(e.target.value))}
                  id="threads-range-slider"
                  className="w-full accent-glow-bright"
                />
                <p className="text-[10px] text-text-muted font-mono leading-normal">
                  ⚠️ High parallel counts utilize significant local GPU memory. Trims runtimes but may bottleneck AST tracing speeds.
                </p>
              </div>
            </div>

            {/* Log Density Select input */}
            <div className="space-y-3 pt-4 border-t border-white/5">
              <label htmlFor="log-density-select" className="text-xs font-semibold font-mono uppercase tracking-wider text-text-muted block">Diagnostic log density</label>
              <select
                id="log-density-select"
                value={logDensity}
                onChange={(e) => setLogDensity(e.target.value)}
                className="w-full bg-black/30 text-text-primary text-xs p-3 rounded-xl border border-white/10 focus:outline-none focus:border-glow-blue transition"
              >
                <option value="compact">COMPACT (Exceptions only)</option>
                <option value="verbose">VERBOSE (Full trace AST checks & API codes)</option>
                <option value="silent">SILENT (Zero telemetry output writes)</option>
              </select>
            </div>

            {/* Save Buttons */}
            <div className="pt-4 border-t border-white/5 flex items-center justify-end gap-3 shrink-0">
              {saveSuccess && (
                <span className="text-xs text-success-custom font-mono flex items-center gap-1 animate-fadeIn">
                  <CheckCircle className="w-4 h-4" />
                  Configurations saved successfully!
                </span>
              )}
              <button
                type="button"
                onClick={handleSave}
                id="btn-settings-save"
                className="px-6 py-2 bg-glow-blue hover:bg-opacity-95 text-slate-950 font-bold text-xs rounded-xl uppercase tracking-wider transition-all duration-300 pointer shadow-lg shadow-cyan-500/10"
              >
                Apply Parameters
              </button>
            </div>

          </div>
        </div>

        {/* Security column */}
        <div className="space-y-6">
          <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl p-5 space-y-4">
            <h3 className="text-sm font-semibold text-[#E6EDF3] border-b border-white/5 pb-3 flex items-center gap-2 font-display">
              <Shield className="w-4 h-4 text-glow-blue" />
              <span>Identity Vault</span>
            </h3>

            <div className="space-y-2 text-xs">
              <label htmlFor="input-settings-key" className="text-[#7D8DA1] font-mono text-[9px] uppercase font-semibold">Local API Gateway Secrets Key</label>
              <input
                id="input-settings-key"
                type="password"
                placeholder="Enter secrets identifier..."
                value={apiSecret}
                onChange={(e) => setApiSecret(e.target.value)}
                className="w-full bg-black/30 text-text-primary p-2.5 rounded-xl border border-white/10 focus:outline-none focus:border-glow-blue text-xs font-mono"
              />
              <span className="block text-[9px] text-text-muted leading-relaxed font-mono">
                🔒 Environment credentials are piped relative to target workspace containers only. They are never transmitted or processed on public domains.
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
