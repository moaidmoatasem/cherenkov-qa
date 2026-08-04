/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect } from 'react';
import { Cpu, Zap, Layers, CheckCircle2, Save, AlertCircle } from 'lucide-react';
import { Card, Skeleton } from '../../ui';
import { fetchSettings, updateSettings, SystemSettings } from '../../../lib/api';
import { useToast } from '../../ui/Toast';

interface ProviderOption {
  id: string;
  name: string;
  isLocal: boolean;
  models: string[];
}

const PROVIDERS: ProviderOption[] = [
  { id: 'ollama', name: 'Ollama (Local)', isLocal: true, models: ['qwen2.5-coder:7b', 'deepseek-r1:8b', 'qwen2.5-vl:7b', 'llama3.2:3b'] },
  { id: 'openai', name: 'OpenAI', isLocal: false, models: ['gpt-4o-mini', 'gpt-4o', 'gpt-4-turbo'] },
  { id: 'anthropic', name: 'Anthropic', isLocal: false, models: ['claude-3-5-sonnet', 'claude-3-opus', 'claude-3-haiku'] },
  { id: 'azure', name: 'Azure OpenAI', isLocal: false, models: ['gpt-4o', 'gpt-4-turbo'] },
  { id: 'bedrock', name: 'AWS Bedrock', isLocal: false, models: ['anthropic.claude-3-5-sonnet', 'meta.llama3-70b-instruct'] },
  { id: 'localai', name: 'LocalAI', isLocal: true, models: ['llava', 'qwen2.5-coder:7b'] },
  { id: 'nemoclaw', name: 'NemoClaw', isLocal: true, models: ['nemotron-nano-4b', 'nemotron-super-49b', 'nemotron-vlm-4b'] },
  { id: 'vlm', name: 'VLM Provider', isLocal: false, models: ['llava', 'bakllava'] },
];

export const ModelProviderSettings: React.FC = () => {
  const [settings, setSettings] = useState<SystemSettings | null>(null);
  const [selectedProvider, setSelectedProvider] = useState('ollama');
  const [selectedModel, setSelectedModel] = useState('qwen2.5-coder:7b');
  const [modelTier, setModelTier] = useState<'small' | 'deep' | 'vision'>('deep');
  const [airllmEnabled, setAirllmEnabled] = useState(false);
  const [airllmModel, setAirllmModel] = useState('Qwen2.5-Coder-32B');
  const [airllmCompression, setAirllmCompression] = useState('4bit');
  const [airllmShardsPath, setAirllmShardsPath] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const { toast } = useToast();

  const loadSettings = async () => {
    try {
      setIsLoading(true);
      const data = await fetchSettings().catch(() => null);
      if (data) {
        setSettings(data);
        const provider = (data as any).model || 'ollama';
        setSelectedProvider(provider);
        
        const airllm = (data as any).airllm;
        if (airllm) {
          setAirllmEnabled(!!airllm.enabled);
          setAirllmModel(airllm.model || 'Qwen2.5-Coder-32B');
          setAirllmCompression(airllm.compression || '4bit');
          setAirllmShardsPath(airllm.layer_shards_path || '');
        }
        
        const tier = data.engine?.model_tier || 'deep';
        setModelTier(tier as any);
        
        // Set default model based on provider
        const providerOpt = PROVIDERS.find(p => p.id === provider);
        if (providerOpt && providerOpt.models.length > 0) {
          setSelectedModel(providerOpt.models[0]);
        }
      }
    } catch (err) {
      toast(`Failed to load settings: ${(err as Error).message}`, 'error');
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
      await updateSettings({
        ...settings,
        model: selectedProvider,
        engine: {
          ...settings.engine,
          model_tier: modelTier,
        },
        airllm: {
          enabled: airllmEnabled,
          model: airllmModel,
          compression: airllmCompression,
          layer_shards_path: airllmShardsPath,
        },
      });
      setMessage('Model provider settings updated successfully!');
      setTimeout(() => setMessage(null), 3000);
    } catch (err) {
      const msg = (err as Error).message;
      setMessage(msg);
      toast(msg, 'error');
    } finally {
      setIsSaving(false);
    }
  };

  const currentProvider = PROVIDERS.find(p => p.id === selectedProvider);

  return (
    <Card className="p-6 space-y-4 font-mono text-xs" data-testid="model-provider-settings">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-wider text-text-muted flex items-center gap-2">
            <Cpu className="w-4 h-4 text-cyan-400" />
            <span>LLM Provider & Model Configuration</span>
          </h2>
          <p className="text-xs text-text-muted mt-0.5 font-sans">
            Select your preferred LLM provider, model tier, and advanced AirLLM options.
          </p>
        </div>
        <button
          onClick={handleSave}
          disabled={isSaving || !settings}
          className="px-4 py-2 bg-cyan-500/20 text-cyan-400 border border-cyan-500/40 rounded-lg font-bold flex items-center gap-1 hover:bg-cyan-500/30 transition cursor-pointer"
          data-testid="btn-save-model-provider"
        >
          <Save className="w-4 h-4" />
          <span>{isSaving ? 'Saving...' : 'Save Settings'}</span>
        </button>
      </div>

      {isLoading ? (
        <Skeleton className="h-48 w-full rounded-xl" />
      ) : !settings ? (
        <div className="p-3 text-rose-400">Failed to load model provider settings.</div>
      ) : (
        <div className="space-y-4">
          {/* Provider Selection */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {PROVIDERS.map((provider) => (
              <button
                key={provider.id}
                onClick={() => {
                  setSelectedProvider(provider.id);
                  if (provider.models.length > 0) {
                    setSelectedModel(provider.models[0]);
                  }
                }}
                className={`p-3 rounded-xl border text-left transition-all ${
                  selectedProvider === provider.id
                    ? 'bg-cyan-500/20 border-cyan-500/40 ring-2 ring-cyan-500/30'
                    : 'bg-black/20 border-white/10 hover:border-white/20'
                }`}
                data-testid={`provider-${provider.id}`}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="font-semibold text-text-primary">{provider.name}</span>
                  {provider.isLocal ? (
                    <Zap className="w-3 h-3 text-emerald-400" title="Local provider" />
                  ) : (
                    <Layers className="w-3 h-3 text-blue-400" title="Cloud provider" />
                  )}
                </div>
                <p className="text-[10px] text-text-muted">
                  {provider.models.length} model{provider.models.length !== 1 ? 's' : ''} available
                </p>
              </button>
            ))}
          </div>

          {/* Model Selection */}
          <div className="space-y-2">
            <label className="text-[10px] uppercase text-text-muted">Selected Model</label>
            <select
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
              className="w-full bg-bg-base text-text-primary p-2.5 rounded-lg border border-white/10"
              data-testid="model-select"
            >
              {currentProvider?.models.map((model) => (
                <option key={model} value={model}>{model}</option>
              ))}
            </select>
          </div>

          {/* Model Tier */}
          <div className="space-y-2">
            <label className="text-[10px] uppercase text-text-muted">Model Tier (Task Routing)</label>
            <div className="grid grid-cols-3 gap-3">
              {[
                { id: 'small', label: 'Small (Fast)', desc: 'Local, quick tasks' },
                { id: 'deep', label: 'Deep (Reasoning)', desc: 'Complex analysis' },
                { id: 'vision', label: 'Vision (VLM)', desc: 'Visual UI testing' },
              ].map((tier) => (
                <button
                  key={tier.id}
                  onClick={() => setModelTier(tier.id as any)}
                  className={`p-3 rounded-xl border text-left transition-all ${
                    modelTier === tier.id
                      ? 'bg-cyan-500/20 border-cyan-500/40 ring-2 ring-cyan-500/30'
                      : 'bg-black/20 border-white/10 hover:border-white/20'
                  }`}
                  data-testid={`tier-${tier.id}`}
                >
                  <p className="font-semibold text-text-primary">{tier.label}</p>
                  <p className="text-[10px] text-text-muted">{tier.desc}</p>
                </button>
              ))}
            </div>
          </div>

          {/* AirLLM Heavy Mode Toggle */}
          <div className="p-4 rounded-xl bg-black/20 border border-white/10 space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Zap className={`w-4 h-4 ${airllmEnabled ? 'text-yellow-400' : 'text-text-muted'}`} />
                <span className="font-semibold text-text-primary">AirLLM Heavy Mode</span>
              </div>
              <button
                onClick={() => setAirllmEnabled(!airllmEnabled)}
                className={`w-12 h-6 rounded-full transition-colors relative ${
                  airllmEnabled ? 'bg-cyan-500' : 'bg-white/10'
                }`}
                data-testid="airllm-toggle"
              >
                <div
                  className={`absolute top-1 w-4 h-4 rounded-full bg-white transition-transform ${
                    airllmEnabled ? 'left-7' : 'left-1'
                  }`}
                />
              </button>
            </div>

            {airllmEnabled && (
              <div className="space-y-3 pl-6 border-l-2 border-white/10">
                <div className="space-y-2">
                  <label className="text-[10px] uppercase text-text-muted">AirLLM Model</label>
                  <input
                    type="text"
                    value={airllmModel}
                    onChange={(e) => setAirllmModel(e.target.value)}
                    className="w-full bg-bg-base text-text-primary p-2 rounded-lg border border-white/10"
                    placeholder="Qwen2.5-Coder-32B"
                    data-testid="airllm-model"
                  />
                </div>

                <div className="space-y-2">
                  <label className="text-[10px] uppercase text-text-muted">Compression Level</label>
                  <select
                    value={airllmCompression}
                    onChange={(e) => setAirllmCompression(e.target.value)}
                    className="w-full bg-bg-base text-text-primary p-2 rounded-lg border border-white/10"
                    data-testid="airllm-compression"
                  >
                    <option value="4bit">4-bit (Maximum compression)</option>
                    <option value="8bit">8-bit (Balanced)</option>
                    <option value="none">None (Full precision)</option>
                  </select>
                </div>

                <div className="space-y-2">
                  <label className="text-[10px] uppercase text-text-muted">Layer Shards Path (Optional)</label>
                  <input
                    type="text"
                    value={airllmShardsPath}
                    onChange={(e) => setAirllmShardsPath(e.target.value)}
                    className="w-full bg-bg-base text-text-primary p-2 rounded-lg border border-white/10"
                    placeholder="~/.cherenkov/shards"
                    data-testid="airllm-shards"
                  />
                </div>

                <div className="flex items-start gap-2 p-2 bg-yellow-500/10 border border-yellow-500/30 rounded-lg">
                  <AlertCircle className="w-4 h-4 text-yellow-400 shrink-0 mt-0.5" />
                  <p className="text-[10px] text-yellow-400">
                    AirLLM enables running large models (32B+) on consumer GPUs with layer-wise inference. 
                    Requires additional setup and disk space for model shards.
                  </p>
                </div>
              </div>
            )}
          </div>

          {message && (
            <div className={`p-3 rounded-xl text-xs flex items-center gap-2 ${
              message.includes('success') 
                ? 'bg-emerald-500/10 border border-emerald-500/30 text-emerald-400' 
                : 'bg-rose-500/10 border border-rose-500/30 text-rose-400'
            }`}>
              <CheckCircle2 className="w-4 h-4" />
              <span>{message}</span>
            </div>
          )}
        </div>
      )}
    </Card>
  );
};

export default ModelProviderSettings;
