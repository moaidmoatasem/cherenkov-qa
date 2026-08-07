/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect } from 'react';
import { Card, Skeleton } from '../../ui';
import { fetchSettings, updateSettings, fetchGovernance, SystemSettings } from '../../../lib/api';
import { Settings, ShieldCheck, Sliders, CheckCircle2, Save } from 'lucide-react';

export const GovernanceSettings: React.FC = () => {
  const [settings, setSettings] = useState<SystemSettings | null>(null);
  const [governance, setGovernance] = useState<{ score: number; issues: any[] }>({ score: 100, issues: [] });
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const loadSettings = async () => {
    try {
      setIsLoading(true);
      const [sData, gData] = await Promise.all([
        fetchSettings().catch(() => null),
        fetchGovernance().catch(() => ({ score: 100, issues: [] })),
      ]);
      setSettings(sData);
      setGovernance(gData);
    } catch {
      setSettings(null);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadSettings();
  }, []);

  const handleSave = async () => {
    if (!settings) return;
    setIsSaving(true);
    setMessage(null);
    try {
      await updateSettings(settings);
      setMessage('Governance & System settings updated successfully!');
      setTimeout(() => setMessage(null), 3000);
    } catch (err) {
      setMessage((err as Error).message);
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <Card className="p-6 space-y-4 font-mono text-xs" data-testid="governance-settings">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-wider text-text-muted flex items-center gap-2">
            <Sliders className="w-4 h-4 text-cyan-400" />
            <span>Governance Rules & Engine Settings</span>
          </h2>
          <p className="text-xs text-text-muted mt-0.5 font-sans">
            System configuration from <code className="font-mono">/api/v1/settings</code> and governance score from <code className="font-mono">/api/v1/governance</code>.
          </p>
        </div>
        <button
          onClick={handleSave}
          disabled={isSaving || !settings}
          className="px-4 py-2 bg-cyan-500/20 text-cyan-400 border border-cyan-500/40 rounded-lg font-bold flex items-center gap-1 hover:bg-cyan-500/30 transition cursor-pointer"
          data-testid="btn-save-governance-settings"
        >
          <Save className="w-4 h-4" />
          <span>{isSaving ? 'Saving...' : 'Save Settings'}</span>
        </button>
      </div>

      {isLoading ? (
        <Skeleton className="h-32 w-full rounded-xl" />
      ) : !settings ? (
        <div className="p-3 text-rose-400">Failed to load system settings.</div>
      ) : (
        <div className="space-y-4">
          {/* Governance Score */}
          <div className="p-4 rounded-xl bg-black/20 border border-white/5 flex items-center justify-between">
            <div>
              <p className="text-[10px] uppercase text-text-muted">System Compliance Score</p>
              <p className="text-xl font-bold text-emerald-400 mt-0.5">{governance.score}/100 Grade A</p>
            </div>
            <ShieldCheck className="w-8 h-8 text-emerald-400" />
          </div>

          {/* Target Host Settings */}
          <div className="space-y-2">
            <label className="text-[10px] uppercase text-text-muted">Target Host URL</label>
            <input
              type="text"
              value={settings.target?.url || ''}
              onChange={(e) =>
                setSettings({
                  ...settings,
                  target: { ...settings.target, url: e.target.value },
                })
              }
              className="w-full bg-bg-base text-text-primary p-2.5 rounded-lg border border-white/10"
              data-testid="setting-target-url"
            />
          </div>

          {/* Egress Policy & Model Tier */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <label className="text-[10px] uppercase text-text-muted">Egress Network Policy</label>
              <select
                value={settings.security?.egress_policy || 'internal'}
                onChange={(e) =>
                  setSettings({
                    ...settings,
                    security: { ...settings.security, egress_policy: e.target.value },
                  })
                }
                className="w-full bg-bg-base text-cyan-400 p-2.5 rounded-lg border border-white/10"
              >
                <option value="none font-mono">Sovereign (No egress)</option>
                <option value="internal">Internal VPC Only</option>
                <option value="any">Any Internet Target</option>
              </select>
            </div>

            <div className="space-y-2">
              <label className="text-[10px] uppercase text-text-muted">Active Model Provider</label>
              <div
                className="w-full bg-bg-base text-cyan-400 p-2.5 rounded-lg border border-white/10"
                data-testid="setting-model-provider"
              >
                {settings.model || 'unset'}
              </div>
              <p className="text-[10px] text-text-muted">
                Read from <code className="font-mono">PROVIDER</code> — managed in the Model Provider panel.
              </p>
            </div>
          </div>

          {/* Copilot Autonomy & Substrate Budgets */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="space-y-2">
              <label className="text-[10px] uppercase text-text-muted">Copilot Autonomy</label>
              <select
                value={settings.copilot?.autonomy || 'assisted'}
                onChange={(e) =>
                  setSettings({
                    ...settings,
                    copilot: { ...settings.copilot, autonomy: e.target.value },
                  })
                }
                className="w-full bg-bg-base text-cyan-400 p-2.5 rounded-lg border border-white/10"
              >
                <option value="assisted">Assisted</option>
                <option value="autonomous">Autonomous</option>
                <option value="supervisor">Supervisor</option>
              </select>
            </div>

            <div className="space-y-2">
              <label className="text-[10px] uppercase text-text-muted">Max Cost USD / Run</label>
              <input
                type="number"
                step="0.1"
                min="0"
                value={settings.substrate?.budgets?.max_cost_usd_per_run ?? 0.0}
                onChange={(e) =>
                  setSettings({
                    ...settings,
                    substrate: {
                      ...settings.substrate,
                      budgets: {
                        ...(settings.substrate?.budgets || { max_latency_ms: 120000 }),
                        max_cost_usd_per_run: parseFloat(e.target.value) || 0,
                      },
                    },
                  })
                }
                className="w-full bg-bg-base text-text-primary p-2.5 rounded-lg border border-white/10"
              />
            </div>

            <div className="space-y-2">
              <label className="text-[10px] uppercase text-text-muted">Max Latency (ms)</label>
              <input
                type="number"
                step="1000"
                min="0"
                value={settings.substrate?.budgets?.max_latency_ms ?? 120000}
                onChange={(e) =>
                  setSettings({
                    ...settings,
                    substrate: {
                      ...settings.substrate,
                      budgets: {
                        ...(settings.substrate?.budgets || { max_cost_usd_per_run: 0.0 }),
                        max_latency_ms: parseInt(e.target.value, 10) || 0,
                      },
                    },
                  })
                }
                className="w-full bg-bg-base text-text-primary p-2.5 rounded-lg border border-white/10"
              />
            </div>
          </div>

          {message && (
            <div className="p-3 bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 rounded-xl text-xs flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4" />
              <span>{message}</span>
            </div>
          )}
        </div>
      )}
    </Card>
  );
};

export default GovernanceSettings;
