/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useEffect, useState } from 'react';
import { Card } from '../../ui';
import { useDensity, setDensity, type Density } from '../../../lib/useDensity';
import { fetchSettings, updateSettings, SystemSettings } from '../../../lib/api';
import { Accessibility, Gauge, Save, CheckCircle2 } from 'lucide-react';

type MotionPref = 'system' | 'reduce' | 'no-preference';

const MOTION_KEY = 'prefers-reduced-motion';

function readMotion(): MotionPref {
  try {
    const value = localStorage.getItem(MOTION_KEY);
    if (value === 'reduce') return 'reduce';
    if (value === 'no-preference') return 'no-preference';
    return 'system';
  } catch {
    return 'system';
  }
}

function setMotion(pref: MotionPref): void {
  try {
    if (pref === 'system') {
      localStorage.removeItem(MOTION_KEY);
    } else {
      localStorage.setItem(MOTION_KEY, pref);
    }
  } catch {
    /* storage full or blocked -- the session still gets the override */
  }
  document.documentElement.dataset.motion = pref === 'reduce' ? 'reduce' : 'full';
  window.dispatchEvent(new CustomEvent('reduced-motion-changed'));
}

export const A11ySettings: React.FC = () => {
  const density = useDensity();
  const [motion, setMotionPref] = useState<MotionPref>(readMotion);
  const [settings, setSettings] = useState<SystemSettings | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    fetchSettings().then((data) => {
      setSettings(data);
      if (data.ui) {
        if (data.ui.density) setDensity(data.ui.density as Density);
        if (data.ui.motion) {
          setMotionPref(data.ui.motion as MotionPref);
          setMotion(data.ui.motion as MotionPref);
        }
      }
    }).catch(() => null);
  }, []);

  // Re-apply the persisted motion override to <html> on load so the CSS guard
  // is in effect even before this panel is visited.
  useEffect(() => {
    document.documentElement.dataset.motion =
      readMotion() === 'reduce' ? 'reduce' : 'full';
  }, []);

  const chooseDensity = (next: Density) => {
    setDensity(next);
    if (settings) {
      setSettings({ ...settings, ui: { ...settings.ui, density: next, motion: settings.ui?.motion || motion } });
    }
  };

  const chooseMotion = (next: MotionPref) => {
    setMotionPref(next);
    setMotion(next);
    if (settings) {
      setSettings({ ...settings, ui: { ...settings.ui, motion: next, density: settings.ui?.density || density } });
    }
  };

  const handleSave = async () => {
    if (!settings) return;
    setIsSaving(true);
    setMessage(null);
    try {
      await updateSettings(settings);
      setMessage('A11y settings updated successfully!');
      setTimeout(() => setMessage(null), 3000);
    } catch (err) {
      setMessage((err as Error).message);
    } finally {
      setIsSaving(false);
    }
  };

  const motionOptions: { value: MotionPref; label: string; hint: string; testid: string }[] = [
    {
      value: 'system',
      label: 'System default',
      hint: 'Follow the operating system setting',
      testid: 'motion-system',
    },
    {
      value: 'reduce',
      label: 'Reduce motion',
      hint: 'Disable decorative animation and transitions',
      testid: 'motion-reduce',
    },
    {
      value: 'no-preference',
      label: 'Full motion',
      hint: 'Show all animation even if the OS asks for less',
      testid: 'motion-full',
    },
  ];

  const densityOptions: { value: Density; label: string; hint: string; testid: string }[] = [
    { value: 'comfortable', label: 'Comfortable', hint: 'Standard spacing', testid: 'density-comfortable' },
    { value: 'compact', label: 'Compact', hint: 'Tighter spacing for dense work', testid: 'density-compact' },
  ];

  return (
    <Card className="p-6 space-y-4 font-mono text-xs" data-testid="a11y-settings">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-wider text-text-muted flex items-center gap-2">
            <Accessibility className="w-4 h-4 text-cyan-400" />
            <span>Accessibility & Display</span>
          </h2>
          <p className="text-xs text-text-muted mt-0.5 font-sans">
            Motion and density preferences are synced with the server.
          </p>
        </div>
        <button
          onClick={handleSave}
          disabled={isSaving || !settings}
          className="px-4 py-2 bg-cyan-500/20 text-cyan-400 border border-cyan-500/40 rounded-lg font-bold flex items-center gap-1 hover:bg-cyan-500/30 transition cursor-pointer"
          data-testid="btn-save-a11y-settings"
        >
          <Save className="w-4 h-4" />
          <span>{isSaving ? 'Saving...' : 'Save Settings'}</span>
        </button>
      </div>

      {/* Motion preference */}
      <fieldset>
        <legend className="text-[10px] uppercase text-text-muted mb-2 flex items-center gap-1.5">
          <Accessibility className="w-3.5 h-3.5" /> Motion
        </legend>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
          {motionOptions.map((opt) => (
            <label
              key={opt.value}
              className={`flex items-start gap-2 p-3 rounded-xl border cursor-pointer transition ${
                motion === opt.value
                  ? 'border-cyan-500/40 bg-cyan-500/10'
                  : 'border-white/10 bg-black/20 hover:border-white/20'
              }`}
            >
              <input
                type="radio"
                name="motion-preference"
                value={opt.value}
                checked={motion === opt.value}
                onChange={() => chooseMotion(opt.value)}
                data-testid={opt.testid}
                className="mt-0.5 accent-cyan-400"
              />
              <span className="leading-tight">
                <span className="block text-text-primary">{opt.label}</span>
                <span className="block text-[10px] text-text-muted font-sans mt-0.5">{opt.hint}</span>
              </span>
            </label>
          ))}
        </div>
      </fieldset>

      {/* Density */}
      <fieldset>
        <legend className="text-[10px] uppercase text-text-muted mb-2 flex items-center gap-1.5">
          <Gauge className="w-3.5 h-3.5" /> Density
        </legend>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
          {densityOptions.map((opt) => (
            <label
              key={opt.value}
              className={`flex items-start gap-2 p-3 rounded-xl border cursor-pointer transition ${
                density === opt.value
                  ? 'border-cyan-500/40 bg-cyan-500/10'
                  : 'border-white/10 bg-black/20 hover:border-white/20'
              }`}
            >
              <input
                type="radio"
                name="ui-density"
                value={opt.value}
                checked={density === opt.value}
                onChange={() => chooseDensity(opt.value)}
                data-testid={opt.testid}
                className="mt-0.5 accent-cyan-400"
              />
              <span className="leading-tight">
                <span className="block text-text-primary">{opt.label}</span>
                <span className="block text-[10px] text-text-muted font-sans mt-0.5">{opt.hint}</span>
              </span>
            </label>
          ))}
        </div>
      </fieldset>

      {message && (
        <div className="p-3 bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 rounded-xl text-xs flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4" />
          <span>{message}</span>
        </div>
      )}
    </Card>
  );
};

export default A11ySettings;
