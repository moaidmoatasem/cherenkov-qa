import React, { useState, useEffect } from 'react';
import { Sparkles, LayoutDashboard, CheckSquare, Brain } from 'lucide-react';
import { Card } from './ui';
import { fetchHealth } from '../lib/api';
import { invokeDesktop, HardwareInfo } from '../lib/tauri';

const WORKFLOW_STAGES = [
  {
    icon: Sparkles,
    title: 'Generate',
    body: "Bring an OpenAPI spec. Cherenkov's AI writes the test suite for you -- no scripting needed to get your first run.",
  },
  {
    icon: LayoutDashboard,
    title: 'Validate',
    body: 'Run those tests against your real API. You get an honest pass/fail against the spec, not a guess.',
  },
  {
    icon: CheckSquare,
    title: 'Triage',
    body: "Anything the AI wasn't sure about waits for you here. Nothing is changed without a human saying yes.",
  },
  {
    icon: Brain,
    title: 'Knowledge',
    body: 'Cherenkov remembers what it learns about your API, so the next run is sharper than the last.',
  },
];

interface OnboardingWizardProps {
  onComplete: () => void;
  onEnableDemo: () => void;
}

export default function OnboardingWizard({ onComplete, onEnableDemo }: OnboardingWizardProps) {
  const [step, setStep] = useState(1);
  const [engineStatus, setEngineStatus] = useState<'checking' | 'online' | 'offline'>('checking');
  const [ollamaStatus, setOllamaStatus] = useState<'checking' | 'found' | 'missing'>('checking');

  useEffect(() => {
    let mounted = true;
    const checkSystem = async (attempt = 0) => {
      // In the desktop shell, the native prerequisite check is authoritative
      // for Ollama; the HTTP health probe below still decides engine status.
      const hw = await invokeDesktop<HardwareInfo>('check_prerequisites');
      if (mounted && hw) {
        setOllamaStatus(hw.has_ollama ? 'found' : 'missing');
      }
      try {
        const h = await fetchHealth();
        if (mounted) {
          setEngineStatus('online');
          if (!hw) {
            // `device` is the only field here backed by a live probe
            // (detect_ollama_device actually calls the Ollama daemon); the
            // backend's "not detected" sentinel is "UNKNOWN" (see
            // cherenkov/core/settings.py / init_cmd.py). `gen_model` is just
            // the *configured* model name from settings — it is set to a
            // real-looking value even when Ollama isn't installed at all,
            // so it must never be treated as a positive detection signal.
            const ollamaReady = !!h.device && h.device.toUpperCase() !== 'UNKNOWN';
            if (ollamaReady) {
              setOllamaStatus('found');
            } else if (attempt < 3) {
              // Retry up to 3 times — device cache warms up within ~5s
              setTimeout(() => { if (mounted) checkSystem(attempt + 1); }, 2000);
            } else {
              setOllamaStatus('missing');
            }
          }
        }
      } catch (e) {
        if (mounted) setEngineStatus('offline');
      }
    };
    checkSystem();
    return () => { mounted = false; };
  }, []);

  const handleNext = () => setStep(s => s + 1);

  // Esc dismissed nothing here, and there was no skip affordance, so the first
  // thing the product did was block the user behind four modal steps with no
  // way out.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onComplete();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onComplete]);

  const handleDemo = () => {
    onEnableDemo();
    handleNext();
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-bg-base/95 backdrop-blur-md"
      role="dialog"
      aria-modal="true"
      aria-label="Welcome to Cherenkov"
    >
      <Card className="relative w-full max-w-2xl p-8 space-y-6 bg-surface-1/90 border border-white/10 shadow-2xl">
        <button
          type="button"
          onClick={onComplete}
          data-testid="onboarding-skip"
          className="absolute top-4 right-4 px-3 py-1.5 rounded-lg text-[11px] font-mono text-text-muted hover:text-text-primary hover:bg-white/5 transition"
        >
          Skip &amp; explore (Esc)
        </button>
        {step === 1 && (
          <div className="space-y-4 text-center">
            <h1 className="text-3xl font-display font-bold text-text-primary">Welcome to CHERENKOV</h1>
            <p className="text-[#7D8DA1] text-sm">
              The UI-first, zero-config API conformance testing suite for QA engineers.
            </p>
            <div className="py-6 flex justify-center">
              <div className="w-24 h-24 rounded-full bg-gradient-to-tr from-cyan-500 to-blue-600 flex items-center justify-center animate-pulse">
                <span className="text-white font-bold text-xl">C</span>
              </div>
            </div>
            <button onClick={handleNext} className="w-full py-3 bg-glow-blue text-slate-950 font-bold rounded-xl uppercase tracking-wider hover:bg-opacity-90 transition">
              Get Started
            </button>
          </div>
        )}

        {step === 2 && (
          <div className="space-y-6">
            <h2 className="text-2xl font-display font-semibold text-text-primary">System Preflight</h2>
            <div className="space-y-4 text-sm text-[#7D8DA1]">
              <div className="flex justify-between items-center p-4 bg-white/5 rounded-lg border border-white/10">
                <span>FastAPI Engine</span>
                {engineStatus === 'checking' ? <span className="text-yellow-500">Checking...</span> :
                 engineStatus === 'online' ? <span className="text-green-400 font-medium">Online</span> :
                 <span className="text-red-400 font-medium">Offline</span>}
              </div>
              <div className="flex justify-between items-center p-4 bg-white/5 rounded-lg border border-white/10">
                <span>Ollama Local LLM</span>
                {ollamaStatus === 'checking' ? <span className="text-yellow-500">Checking...</span> :
                 ollamaStatus === 'found' ? <span className="text-green-400 font-medium">Detected</span> :
                 <span className="text-orange-400 font-medium">Not Detected (Demo Mode Fallback)</span>}
              </div>
            </div>

            <div className="flex space-x-4 pt-4">
              {ollamaStatus === 'missing' ? (
                <button onClick={handleDemo} className="flex-1 py-3 bg-orange-500/20 text-orange-400 border border-orange-500/50 font-bold rounded-xl hover:bg-orange-500/30 transition">
                  Continue in Demo Mode
                </button>
              ) : (
                <button onClick={handleNext} className="flex-1 py-3 bg-glow-blue text-slate-950 font-bold rounded-xl hover:bg-opacity-90 transition">
                  Continue
                </button>
              )}
            </div>
          </div>
        )}

        {step === 3 && (
          <div className="space-y-6">
            <div className="text-center space-y-1">
              <h2 className="text-2xl font-display font-semibold text-text-primary">Your new workflow</h2>
              <p className="text-[#7D8DA1] text-sm">
                Coming from manual testing? This is the whole loop -- start to finish, no automation background required.
              </p>
            </div>
            <div className="space-y-3">
              {WORKFLOW_STAGES.map((stage, idx) => {
                const Icon = stage.icon;
                return (
                  <div key={stage.title} className="flex items-start gap-3 p-3 bg-white/5 rounded-lg border border-white/10">
                    <div className="w-7 h-7 rounded-full bg-cyan-500/15 border border-cyan-500/30 flex items-center justify-center text-cyan-400 shrink-0 text-xs font-bold">
                      {idx + 1}
                    </div>
                    <div className="min-w-0">
                      <div className="flex items-center gap-1.5 text-text-primary font-semibold text-sm">
                        <Icon className="w-3.5 h-3.5 text-cyan-400" />
                        {stage.title}
                      </div>
                      <p className="text-xs text-[#7D8DA1] mt-0.5 leading-relaxed">{stage.body}</p>
                    </div>
                  </div>
                );
              })}
            </div>
            <button onClick={handleNext} className="w-full py-3 bg-glow-blue text-slate-950 font-bold rounded-xl uppercase tracking-wider hover:bg-opacity-90 transition">
              Got it
            </button>
          </div>
        )}

        {step === 4 && (
          <div className="space-y-6 text-center">
            <h2 className="text-2xl font-display font-semibold text-text-primary">You're all set!</h2>
            <p className="text-[#7D8DA1] text-sm leading-relaxed">
              CHERENKOV is ready. Drag and drop an OpenAPI spec on the Generate Tests screen to get your first suite.
            </p>
            <button onClick={onComplete} className="w-full py-3 bg-glow-blue text-slate-950 font-bold rounded-xl uppercase tracking-wider hover:bg-opacity-90 transition">
              Enter Dashboard
            </button>
          </div>
        )}
      </Card>
    </div>
  );
}
