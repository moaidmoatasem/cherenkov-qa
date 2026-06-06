/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect } from 'react';
import { 
  Settings, 
  Cpu, 
  KeyRound, 
  SlidersHorizontal, 
  CheckCircle,
  Database,
  Shield,
  Activity,
  Layers,
  Unlock,
  Coins
} from 'lucide-react';
import CherenkovLogo from './CherenkovLogo';
import { fetchSettings, updateSettings, SystemSettings } from '../lib/api';
import { useToast } from './ui/Toast';
import { Skeleton } from './ui';

export default function SettingsScreen() {
  const [model, setModel] = useState('qwen-coder');
  const [threadLimit, setThreadLimit] = useState(4);
  const [logDensity, setLogDensity] = useState('verbose');
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [apiSecret, setApiSecret] = useState('');

  // Added Redesign Configurations
  const [tier, setTier] = useState<'small' | 'deep' | 'vision' | 'ml'>('deep');
  const [egress, setEgress] = useState<'none' | 'internal' | 'any'>('internal');
  const [budget, setBudget] = useState(15.00);
  const [density, setDensity] = useState<'comfortable' | 'compact'>('comfortable');
  const [reducedMotion, setReducedMotion] = useState(false);

  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [targetSettings, setTargetSettings] = useState({ url: '', auth_header: '' });
  const { toast } = useToast();

  useEffect(() => {
    fetchSettings().then(data => {
      setTargetSettings(data.target || { url: '', auth_header: '' });
      setTier(data.engine.model_tier as any);
      setBudget(data.engine.execution_budget);
      setThreadLimit(data.engine.workers);
      setEgress(data.security.egress_policy as any);
      setApiSecret(data.security.auth_secret || '');
      setDensity(data.ui.density as any);
      setReducedMotion(data.ui.reduced_motion);
      setIsLoading(false);
    }).catch(err => {
      toast(`Failed to load settings: ${(err as Error).message}`, 'error');
      setIsLoading(false);
    });
  }, []);

  const handleSave = async () => {
    setIsSaving(true);
    try {
      await updateSettings({
        target: targetSettings,
        engine: {
          model_tier: tier,
          enable_demo_mode: true,
          execution_budget: budget,
          workers: threadLimit
        },
        security: {
          egress_policy: egress,
          auth_secret: apiSecret
        },
        ui: {
          density,
          reduced_motion: reducedMotion
        }
      });
      localStorage.setItem('[copilot] density', density);
      localStorage.setItem('[copilot] reduced-motion', reducedMotion ? 'true' : 'false');
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 2000);
      toast('Settings saved successfully.', 'success');
    } catch (err) {
      toast(`Failed to save settings: ${(err as Error).message}`, 'error');
    } finally {
      setIsSaving(false);
    }
  };

  if (isLoading) {
    return <div className="p-6 h-full space-y-6"><Skeleton className="h-64 w-full" /></div>;
  }

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
            Configure target copilot execution settings, egress network policies, and user preferences.
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

            {/* Substrate Capability Tiers */}
            <div className="space-y-4 pt-4 border-t border-white/5">
              <h2 className="text-sm font-semibold font-mono uppercase tracking-wider text-text-muted flex items-center gap-2">
                <Layers className="w-4 h-4 text-glow-blue" />
                <span>Substrate Router Capability Tier</span>
              </h2>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs font-mono">
                {(['small', 'deep', 'vision', 'ml'] as const).map((t) => (
                  <button
                    key={t}
                    onClick={() => setTier(t)}
                    className={`py-2 px-3 rounded-xl border transition cursor-pointer uppercase ${
                      tier === t
                        ? 'bg-glow-blue/10 border-glow-blue text-glow-bright font-bold'
                        : 'bg-black/25 border-white/5 text-[#7D8DA1] hover:text-[#E6EDF3]'
                    }`}
                  >
                    {t}
                  </button>
                ))}
              </div>
            </div>

            {/* Egress Network Policies */}
            <div className="space-y-4 pt-4 border-t border-white/5">
              <h2 className="text-sm font-semibold font-mono uppercase tracking-wider text-text-muted flex items-center gap-2">
                <Unlock className="w-4 h-4 text-glow-blue" />
                <span>API Sandbox Egress Policy Dial</span>
              </h2>

              <div className="grid grid-cols-3 gap-2 text-xs font-mono">
                {(['none', 'internal', 'any'] as const).map((e) => (
                  <button
                    key={e}
                    onClick={() => setEgress(e)}
                    className={`py-2 px-3 rounded-xl border transition cursor-pointer uppercase ${
                      egress === e
                        ? 'bg-glow-blue/10 border-glow-blue text-glow-bright font-bold'
                        : 'bg-black/25 border-white/5 text-[#7D8DA1] hover:text-[#E6EDF3]'
                    }`}
                  >
                    {e === 'none' ? 'Sovereign' : e}
                  </button>
                ))}
              </div>
            </div>

            {/* LLM Run Budgets */}
            <div className="space-y-4 pt-4 border-t border-white/5">
              <h2 className="text-sm font-semibold font-mono uppercase tracking-wider text-text-muted flex items-center gap-2">
                <Coins className="w-4 h-4 text-glow-blue" />
                <span>Maximum Run Spend Budget ($)</span>
              </h2>

              <div className="space-y-3">
                <div className="flex justify-between items-center text-xs font-mono text-[#E6EDF3]">
                  <span>SPEND BUDGET LIMIT:</span>
                  <span className="text-glow-bright font-bold">${budget.toFixed(2)} USD</span>
                </div>
                <input
                  type="range"
                  min="1"
                  max="100"
                  step="0.5"
                  value={budget}
                  onChange={(e) => setBudget(Number(e.target.value))}
                  className="w-full accent-glow-bright"
                />
              </div>
            </div>

            {/* Thread limit */}
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
              </div>
            </div>

            {/* Accessibility & UI Densities */}
            <div className="space-y-4 pt-4 border-t border-white/5">
              <h2 className="text-sm font-semibold font-mono uppercase tracking-wider text-text-muted flex items-center gap-2">
                <Activity className="w-4 h-4 text-glow-blue" />
                <span>Interface & Accessibility Settings</span>
              </h2>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs font-mono">
                {/* Density Switch */}
                <div className="flex items-center justify-between p-3 rounded-xl bg-black/25 border border-white/5">
                  <span className="text-[#7D8DA1]">Compact View Mode</span>
                  <input
                    type="checkbox"
                    checked={density === 'compact'}
                    onChange={(e) => setDensity(e.target.checked ? 'compact' : 'comfortable')}
                    className="w-4 h-4 accent-glow-bright"
                  />
                </div>

                {/* Reduced Motion Switch */}
                <div className="flex items-center justify-between p-3 rounded-xl bg-black/25 border border-white/5">
                  <span className="text-[#7D8DA1]">Reduce Motion Animations</span>
                  <input
                    type="checkbox"
                    checked={reducedMotion}
                    onChange={(e) => setReducedMotion(e.target.checked)}
                    className="w-4 h-4 accent-glow-bright"
                  />
                </div>
              </div>
            </div>

            {/* Save Buttons */}
            <div className="pt-4 border-t border-white/5 flex items-center justify-end gap-3 shrink-0">
              {saveSuccess && (
                <span className="text-xs text-[#3FB950] font-mono flex items-center gap-1 animate-fadeIn">
                  <CheckCircle className="w-4 h-4" />
                  Configurations saved successfully!
                </span>
              )}
              <button
                type="button"
                onClick={handleSave}
                disabled={isSaving}
                id="btn-settings-save"
                className="px-6 py-2 bg-glow-blue hover:bg-opacity-95 text-slate-950 font-bold text-xs rounded-xl uppercase tracking-wider transition-all duration-300 pointer shadow-lg shadow-cyan-500/10 disabled:opacity-50"
              >
                {isSaving ? 'Saving...' : 'Apply Parameters'}
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
              <span className="block text-[9px] text-[#7D8DA1]/60 leading-relaxed font-mono">
                🔒 Environment credentials are piped relative to target workspace containers only. They are never transmitted or processed on public domains.
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
