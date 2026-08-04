/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useEffect, useState } from 'react';
import { Card, Skeleton } from '../../ui';
import { useToast } from '../../ui/Toast';
import { fetchSettings, updateSettings, SystemSettings } from '../../../lib/api';
import { Cpu, Layers, Save } from 'lucide-react';

// Mirrors the providers actually wired in cherenkov/substrate/providers/.
const PROVIDERS = ['openai', 'anthropic', 'azure', 'bedrock', 'ollama', 'localai', 'nemoclaw', 'vlm'] as const;

const LOCAL_PROVIDERS = new Set(['ollama', 'localai', 'vlm']);

export const ModelProviderSettings: React.FC = () => {
  const { toast } = useToast();
  const [settings, setSettings] = useState<SystemSettings | null>(null);
  const [provider, setProvider] = useState('ollama');
  const [tier, setTier] = useState('local');
  const [airllmEnabled, setAirllmEnabled] = useState(false);
  const [airllmModel, setAirllmModel] = useState('Qwen2.5-Coder-32B');
  const [airllmCompression, setAirllmCompression] = useState('4bit');
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    fetchSettings()
      .then((data) => {
        setSettings(data);
        setProvider(data.model || 'ollama');
        setTier(data.engine?.model_tier || 'local');
        if (data.airllm) {
          setAirllmEnabled(!!data.airllm.enabled);
          setAirllmModel(data.airllm.model || 'Qwen2.5-Coder-32B');
          setAirllmCompression(data.airllm.compression || '4bit');
        }
      })
      .catch(() => setSettings(null))
      .finally(() => setIsLoading(false));
  }, []);

  const handleSave = async () => {
    if (!settings) return;
    setIsSaving(true);
    try {
      await updateSettings({
        ...settings,
        engine: { ...settings.engine, model_tier: tier },
        model: provider,
        airllm: {
          enabled: airllmEnabled,
          model: airllmModel,
          compression: airllmCompression,
          layer_shards_path: settings.airllm?.layer_shards_path || '',
        },
      });
      toast('Model provider settings saved', 'success');
    } catch (e) {
      toast(`Save failed: ${(e as Error).message}`, 'danger');
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <Card className="p-6 space-y-5" data-testid="model-provider-settings">
      <div className="flex items-start justify-between">
        <div>
          <h2 className="text-sm font-semibold font-mono uppercase tracking-wider text-text-muted flex items-center gap-2">
            <Cpu className="w-4 h-4 text-cyan-400" />
            <span>Model Provider</span>
          </h2>
          <p className="text-xs text-text-muted mt-0.5">
            Which AI writes your tests. Local providers keep everything on your machine; hosted ones call out.
          </p>
        </div>
        <button
          onClick={handleSave}
          disabled={isSaving || !settings}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 text-xs font-mono font-semibold hover:bg-cyan-500/20 transition disabled:opacity-40 cursor-pointer"
          data-testid="btn-save-model-provider"
        >
          <Save className="w-3.5 h-3.5" />
          {isSaving ? 'Saving...' : 'Save'}
        </button>
      </div>

      {isLoading ? (
        <Skeleton className="h-32 w-full rounded-xl" />
      ) : (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs font-mono" data-testid="provider-select">
            {PROVIDERS.map((p) => (
              <button
                key={p}
                onClick={() => setProvider(p)}
                className={`py-2 px-3 rounded-xl border transition cursor-pointer uppercase relative ${
                  provider === p
                    ? 'bg-cyan-500/10 border-cyan-500 text-cyan-400 font-bold'
                    : 'bg-black/25 border-white/5 text-text-muted hover:text-text-primary'
                }`}
              >
                {p}
                {LOCAL_PROVIDERS.has(p) && (
                  <span className="absolute top-1 right-1.5 text-[8px] text-emerald-400" title="Runs locally">
                    ●
                  </span>
                )}
              </button>
            ))}
          </div>
          <p className="text-[10px] text-text-muted font-mono">
            <span className="text-emerald-400">●</span> runs locally — nothing leaves your machine
          </p>

          <div className="space-y-2 pt-4 border-t border-white/5">
            <label className="text-[10px] font-mono uppercase text-text-muted">Model Tier</label>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs font-mono" data-testid="model-tier-select">
              {['local', 'small', 'deep', 'vision'].map((t) => (
                <button
                  key={t}
                  onClick={() => setTier(t)}
                  className={`py-2 px-3 rounded-xl border transition cursor-pointer uppercase ${
                    tier === t
                      ? 'bg-cyan-500/10 border-cyan-500 text-cyan-400 font-bold'
                      : 'bg-black/25 border-white/5 text-text-muted hover:text-text-primary'
                  }`}
                >
                  {t}
                </button>
              ))}
            </div>
          </div>

          <div className="space-y-3 pt-4 border-t border-white/5">
            <div className="flex items-center justify-between p-3 rounded-xl bg-black/25 border border-white/5">
              <div className="flex items-center gap-2">
                <Layers className="w-4 h-4 text-amber-400" />
                <div>
                  <span className="text-text-primary text-xs font-mono">AirLLM Heavy Mode</span>
                  <p className="text-[9px] text-text-muted mt-0.5">
                    Runs 32B+ models via layer-wise inference on consumer GPUs. Slow (30-120s/endpoint) — batch use only.
                  </p>
                </div>
              </div>
              <input
                type="checkbox"
                checked={airllmEnabled}
                onChange={(e) => setAirllmEnabled(e.target.checked)}
                className="w-4 h-4 accent-cyan-400 shrink-0"
                data-testid="toggle-airllm"
              />
            </div>

            {airllmEnabled && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div className="space-y-1">
                  <label className="text-[9px] text-text-muted uppercase font-semibold">Model</label>
                  <select
                    value={airllmModel}
                    onChange={(e) => setAirllmModel(e.target.value)}
                    className="w-full bg-black/30 text-text-primary p-2 rounded-xl border border-white/10 focus:outline-none focus:border-cyan-400 text-xs font-mono"
                  >
                    <option value="Qwen2.5-Coder-32B">Qwen2.5-Coder-32B</option>
                    <option value="DeepSeek-Coder-33B">DeepSeek-Coder-33B</option>
                    <option value="Llama-3-70B">Llama-3-70B</option>
                  </select>
                </div>
                <div className="space-y-1">
                  <label className="text-[9px] text-text-muted uppercase font-semibold">Compression</label>
                  <select
                    value={airllmCompression}
                    onChange={(e) => setAirllmCompression(e.target.value)}
                    className="w-full bg-black/30 text-text-primary p-2 rounded-xl border border-white/10 focus:outline-none focus:border-cyan-400 text-xs font-mono"
                  >
                    <option value="4bit">4-bit (3x faster)</option>
                    <option value="8bit">8-bit (balanced)</option>
                    <option value="none">Full precision</option>
                  </select>
                </div>
              </div>
            )}
          </div>
        </>
      )}
    </Card>
  );
};

export default ModelProviderSettings;
