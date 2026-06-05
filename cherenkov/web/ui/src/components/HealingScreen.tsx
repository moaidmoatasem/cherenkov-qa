/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState } from 'react';
import { 
  Sparkles, 
  HelpCircle, 
  AlertTriangle, 
  CheckCircle, 
  Terminal, 
  X, 
  Check, 
  ArrowRight,
  Eye,
  Settings
} from 'lucide-react';
import { FailingTest } from '../types';
import { INITIAL_FAILURES } from '../mockData';
import { validateSuite, editTestScenario } from '../lib/api';
import { useToast } from './ui/Toast';
import CherenkovLogo from './CherenkovLogo';
import { useToast } from './ui/Toast';

interface HealingScreenProps {
  onSuggestResolveCount: (count: number) => void;
}

export default function HealingScreen({ onSuggestResolveCount }: HealingScreenProps) {
  const { addToast } = useToast();
  const [failures, setFailures] = useState<FailingTest[]>(INITIAL_FAILURES);
  const [appliedIds, setAppliedIds] = useState<string[]>([]);
  const [confirmingId, setConfirmingId] = useState<string | null>(null);
  const [activeTraceLog, setActiveTraceLog] = useState<string | null>(null);

  const handleApply = async (id: string) => {
    setConfirmingId(null);
    const item = failures.find(f => f.id === id);
    if (!item) return;

    try {
      await editTestScenario(id, item.proposedCode);
      addToast(`Successfully applied healing to ${item.name}`, 'success');

      setAppliedIds(prev => [...prev, id]);

      validateSuite('http://localhost:8080/v2').catch(() => {
        addToast('Validation suite trigger failed.', 'warning');
      });

      setTimeout(() => {
        const remaining = failures.filter(f => f.id !== id);
        setFailures(remaining);
        onSuggestResolveCount(remaining.length);
      }, 1500);
    } catch (err) {
      addToast(`Failed to apply healing: ${(err as Error).message}`, 'error');
    }
  };

  const handleDismiss = (id: string) => {
    const remaining = failures.filter(f => f.id !== id);
    setFailures(remaining);
    onSuggestResolveCount(remaining.length);
  };

  const getFailureBadgeColor = (type: string) => {
    switch (type) {
      case 'CONTRACT_DRIFT':
        return 'bg-glow-blue/10 text-glow-bright border-glow-blue/30';
      case 'AUTH_EXPIRY':
        return 'bg-[#D29922]/10 text-[#D29922] border-[#D29922]/35';
      case 'STATE_SEQUENCING':
        return 'bg-[#3FB950]/10 text-[#3FB950] border-[#3FB950]/35';
      case 'NETWORK_FLAKY':
        return 'bg-gray-brand/20 text-[#7D8DA1] border-[#233044]';
      case 'ASSERTION_DRIFT':
        return 'bg-[#F85149]/15 text-[#F85149] border-[#F85149]/40';
      default:
        return 'bg-[#7D8DA1]/10 text-[#7D8DA1] border-none';
    }
  };

  return (
    <div className="p-8 h-full overflow-y-auto space-y-6 grid-bg bg-transparent relative z-10" id="healing-screen">
      
      {/* Page Header */}
      <div className="flex items-center gap-4 border-b border-white/5 pb-4 shrink-0">
        <CherenkovLogo variant="icon" size={42} />
        <div>
          <h1 className="font-display font-bold text-3xl text-text-primary tracking-tight">
            Self-Healing & Drift Redress
          </h1>
          <p className="text-sm text-text-muted mt-1 leading-relaxed">
            Detect schema specification discrepancies and apply deterministic, non-destructive test repairs.
          </p>
        </div>
      </div>

      {/* Top Banner Disclaimer */}
      <div className="border border-glow-blue/20 bg-white/5 backdrop-blur-xl rounded-2xl p-5 relative overflow-hidden flex items-center gap-4 shadow-lg select-none shrink-0" id="healing-banner">
        {/* Glowing floating blur background */}
        <div className="absolute -top-12 -right-12 w-32 h-32 bg-[#2D9CDB] rounded-full blur-[64px] opacity-25" />
        
        <div className="p-3 bg-glow-blue/15 text-glow-bright rounded-full shrink-0">
          <Sparkles className="w-6 h-6 animate-pulse" />
        </div>

        <div>
          <h3 className="font-display font-semibold text-sm text-text-primary tracking-wide">
            Interactive Agent Diagnostic Healing Suggestions
          </h3>
          <p className="text-xs text-[#7D8DA1] mt-1 leading-relaxed">
            API specifications occasionally shift during development. Cherenkov identifies drift and generates surgical code patch recommendations.
            <span className="block font-semibold text-glow-bright font-mono mt-1">All repairs are suggest-only — no files will change without human approval.</span>
          </p>
        </div>
      </div>

      {/* Main Column Listing */}
      <div className="space-y-6 max-w-5xl">
        {failures.length === 0 ? (
          <div className="py-24 border border-dashed border-white/10 rounded-2xl bg-white/5 backdrop-blur-md text-center space-y-4">
            <div className="mx-auto w-12 h-12 rounded-full bg-[#3FB950]/10 text-[#3FB950] flex items-center justify-center">
              <CheckCircle className="w-6 h-6" />
            </div>
            <h3 className="text-lg font-display text-text-primary font-medium">All tests completely healthy</h3>
            <p className="text-text-muted text-xs mx-auto max-w-sm">
              Drift checkers verify Playwright configurations against current microservice deployments. All checks are fully aligned.
            </p>
          </div>
        ) : (
          failures.map((item) => {
            const isApplied = appliedIds.includes(item.id);
            const isConfirming = confirmingId === item.id;
            
            return (
              <div
                key={item.id}
                id={`drift-card-${item.id}`}
                className={`border rounded-2xl bg-white/5 backdrop-blur-md transition-all duration-500 overflow-hidden relative ${
                  isApplied 
                    ? 'border-[#3FB950] bg-[#3FB950]/10 opacity-75 scale-98 translate-y-1' 
                    : 'border-white/10 hover:border-glow-blue/40'
                }`}
              >
                {/* Active Application Flash overlay indicator */}
                {isApplied && (
                  <div className="absolute inset-0 bg-[#3FB950]/20 z-10 flex flex-col items-center justify-center font-mono text-xs font-semibold text-[#3FB950] animate-fadeIn">
                    <Check className="w-8 h-8 text-[#3FB950] animate-bounce" />
                    <span>SUGGESTION APPLIED · PLAYWRIGHT SPEC UPDATED</span>
                  </div>
                )}

                {/* Card Top Title info bar */}
                <div className="p-4 bg-black/40 border-b border-white/5 flex flex-wrap gap-3 items-center justify-between select-none">
                  <div className="flex items-center gap-3">
                    <span className="font-mono text-xs font-bold text-[#E6EDF3] tracking-wide">{item.name}</span>
                    <span className={`px-2 py-0.5 rounded text-[9px] font-mono font-bold uppercase border ${getFailureBadgeColor(item.failureType)}`}>
                      {item.failureType.replace('_', ' ')}
                    </span>
                  </div>

                  <span className="text-[10px] font-mono text-text-muted">DIAGNOSIS BLOCK ID: {item.id}</span>
                </div>

                {/* Diagnosis body */}
                <div className="p-5 space-y-4">
                  
                  {/* Diagnosis first text line */}
                  <div className="space-y-1">
                    <span className="block text-[9px] font-mono uppercase tracking-wider text-text-muted font-bold">Why it failed:</span>
                    <p className="text-xs text-[#E6EDF3] leading-relaxed font-sans">{item.diagnosis}</p>
                  </div>

                  {/* Red-flagged drift bug warning */}
                  {item.hasAssertionWarning && (
                    <div className="p-3 bg-red-500/10 border border-red-500/20 text-red-400 rounded-xl flex items-start gap-2.5 text-xs">
                      <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5 animate-pulse" />
                      <div className="space-y-0.5">
                        <strong className="block font-bold">Potential Server-Side Defect Identified</strong>
                        <span className="text-[11px] text-red-400/90">
                          This failure might stem from a real API regression (HTTP 500 error on checkout table locks), rather than test-suite script drift. Investigate deployment metrics first.
                        </span>
                      </div>
                    </div>
                  )}

                  {/* SIDE-BY-SIDE DIFF VIEWPORT */}
                  <div className="space-y-1.5">
                    <span className="block text-[9px] font-mono uppercase tracking-wider text-text-muted font-bold">Surgical diff proposal</span>
                    
                    <div className="grid grid-cols-1 md:grid-cols-2 border border-white/5 rounded-xl overflow-hidden font-mono text-[11px] bg-black/40">
                      {/* Left: Outdated Code (Removal) */}
                      <div className="border-r border-white/5 flex flex-col justify-between">
                        <div className="bg-white/5 p-1.5 px-3 border-b border-white/5 text-[#7D8DA1] text-[9px]">
                          CURRENT OUTDATED TEST COMPONENT
                        </div>
                        <div className="p-3 bg-red-500/5 text-red-400 overflow-x-auto min-h-24">
                          <pre><code>{item.oldCode}</code></pre>
                        </div>
                      </div>

                      {/* Right: Healed Code (Addition) */}
                      <div className="flex flex-col justify-between">
                        <div className="bg-[#131d31] p-1.5 px-3 border-b border-white/5 text-glow-bright text-[9px]">
                          PROPOSED HEALED TEST COMPONENT
                        </div>
                        <div className="p-3 bg-success-custom/5 text-success-custom/95 overflow-x-auto min-h-24">
                          <pre><code>{item.proposedCode}</code></pre>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Actions Drawer Bar */}
                  <div className="flex justify-between items-center pt-3 border-t border-white/5 bg-white/5 p-2.5 rounded-xl">
                    {/* Log viewer clicker */}
                    <button
                      onClick={() => setActiveTraceLog(item.id)}
                      className="flex items-center gap-1.5 text-xs text-[#7D8DA1] hover:text-glow-bright transition cursor-pointer"
                    >
                      <Eye className="w-3.5 h-3.5" />
                      <span>OPEN EXPLAINER TRACE</span>
                    </button>

                    <div className="flex items-center gap-3">
                      <button
                        onClick={() => handleDismiss(item.id)}
                        className="px-3 py-1.5 text-text-muted hover:text-red-400 transition text-xs font-mono uppercase cursor-pointer"
                      >
                        Dismiss
                      </button>

                      {isConfirming ? (
                        <div className="flex items-center gap-1.5 animate-fadeIn">
                          <span className="text-[10px] font-mono text-[#D29922]">REWRITE AST FILE?</span>
                          <button
                            onClick={() => handleApply(item.id)}
                            className="px-3 py-1 bg-success-custom text-[#FFFFFF] font-bold rounded text-xs font-mono uppercase cursor-pointer"
                          >
                            CONFIRM
                          </button>
                          <button
                            onClick={() => setConfirmingId(null)}
                            className="px-2 py-1 bg-white/10 text-text-[#7D8DA1] rounded text-xs font-mono uppercase cursor-pointer"
                          >
                            CANCEL
                          </button>
                        </div>
                      ) : (
                        <button
                          onClick={() => setConfirmingId(item.id)}
                          className="flex items-center gap-1.5 px-4 py-1.5 bg-glow-blue hover:bg-opacity-95 text-slate-950 font-bold rounded-xl text-xs font-mono uppercase tracking-wider transition shadow cursor-pointer"
                        >
                          <span>APPLY HEALING SUGGESTION</span>
                          <ArrowRight className="w-3 h-3 stroke-[3px]" />
                        </button>
                      )}
                    </div>
                  </div>

                </div>

              </div>
            );
          })
        )}
      </div>

      {/* Floating Trace Modal */}
      {activeTraceLog && (
        <div className="fixed inset-0 bg-black/40 backdrop-blur-md z-50 flex items-center justify-center p-4">
          <div className="bg-[#131d31] backdrop-blur-2xl border border-white/10 rounded-2xl w-full max-w-xl p-6 relative">
            <button
              onClick={() => setActiveTraceLog(null)}
              className="absolute top-4 right-4 text-[#7D8DA1] hover:text-[#E6EDF3] p-1 rounded"
            >
              <X className="w-4 h-4 text-[#7D8DA1]" />
            </button>
            
            <h3 className="font-display font-bold text-lg text-text-primary tracking-tight mb-2">
              APIs contract tracer Playwright logs: {activeTraceLog}
            </h3>

            <div className="space-y-4 text-xs font-mono leading-relaxed mt-4 bg-black/30 p-4 text-[#7D8DA1] border border-white/5 rounded-xl max-h-72 overflow-y-auto">
              [CHERENKOV REPLAY MONITOR]<br />
              &gt; Launching playwright runner process: headless Chromium...<br />
              &gt; Request context instantiated. Target: http://localhost:8080/v2<br />
              <br />
              [TRACE EXCEPTION FOUND]<br />
              &gt; {activeTraceLog === 'fail-1' ? 'Drifting elements matched fields. schema_model: "session_id", actual_response_body: "user_session_token". Update assertion required.' :
                 activeTraceLog === 'fail-2' ? 'Authorization exception. Server returned 401 Unauthorized. token identifier "expired-uuid" expired at 2026-05-30T10:00:00Z.' :
                 activeTraceLog === 'fail-3' ? 'Dependence sequencing mismatch error. Specified DELETE target ID not created in testing database prior to executing test block.' :
                 'DB transaction conflict exception. Read locking threshold timeout after 2500ms parallel executions.'}<br />
              <br />
              &gt; Exit code: <span className="text-red-400">1</span>
            </div>

            <div className="pt-4 flex justify-end">
              <button
                type="button"
                onClick={() => setActiveTraceLog(null)}
                className="px-4 py-1.5 bg-white/5 hover:bg-glow-blue hover:text-slate-950 border border-white/10 text-[#E6EDF3] text-xs font-mono font-semibold rounded-xl uppercase transition cursor-pointer"
              >
                Close Trace console
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
