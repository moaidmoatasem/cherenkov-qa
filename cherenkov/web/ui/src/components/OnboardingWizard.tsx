import React, { useState, useEffect } from 'react';
import { Card } from './ui';
import { fetchHealth } from '../lib/api';

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
    const checkSystem = async () => {
      try {
        const h = await fetchHealth();
        if (mounted) {
          setEngineStatus('online');
          setOllamaStatus(h.ollama_available ? 'found' : 'missing');
        }
      } catch (e) {
        if (mounted) setEngineStatus('offline');
      }
    };
    checkSystem();
    return () => { mounted = false; };
  }, []);

  const handleNext = () => setStep(s => s + 1);

  const handleDemo = () => {
    onEnableDemo();
    onComplete();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-bg-base/95 backdrop-blur-md">
      <Card className="w-full max-w-2xl p-8 space-y-6 bg-surface-1/90 border border-white/10 shadow-2xl">
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
          <div className="space-y-6 text-center">
            <h2 className="text-2xl font-display font-semibold text-text-primary">You're all set!</h2>
            <p className="text-[#7D8DA1] text-sm leading-relaxed">
              CHERENKOV is ready. You can now drag and drop an OpenAPI spec to generate tests, or explore the dashboard.
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
