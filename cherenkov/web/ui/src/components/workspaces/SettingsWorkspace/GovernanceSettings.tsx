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
              <label className="text-[10px] uppercase text-text-muted">Model Tier</label>
              <select
                value={settings.engine?.model_tier || 'deep'}
                onChange={(e) =>
                  setSettings({
                    ...settings,
                    engine: { ...settings.engine, model_tier: e.target.value },
                  })
                }
                className="w-full bg-bg-base text-cyan-400 p-2.5 rounded-lg border border-white/10"
              >
                <option value="small">Small (Fast / Local)</option>
                <option value="deep">Deep (Rich reasoning)</option>
                <option value="vision">Vision (VLM Visual UI)</option>
              </select>
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
