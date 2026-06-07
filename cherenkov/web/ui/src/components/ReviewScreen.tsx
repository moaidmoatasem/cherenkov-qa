/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect, useRef } from 'react';
import { 
  Check, 
  X, 
  AlertTriangle, 
  Edit3, 
  FolderCheck, 
  Tv, 
  Terminal, 
  Sparkles, 
  Code,
  CheckCircle,
  HelpCircle,
  Clock
} from 'lucide-react';
import { TestItem, TestGate } from '../types';
import { approveTestScenario, rejectTestScenario, editTestScenario, fetchGeneratedTests, fetchReviewQueue, ReviewQueueItem, explainTestScenario } from '../lib/api';
import { useToast } from './ui/Toast';
import CherenkovLogo from './CherenkovLogo';
import { Skeleton } from './ui';

interface ReviewScreenProps {
  onUpdatePassRateAndCount: (testCount: number, approvedCount: number) => void;
}

export default function ReviewScreen({ onUpdatePassRateAndCount }: ReviewScreenProps) {
  const { toast } = useToast();
  const [tests, setTests] = useState<TestItem[]>([]);
  const testsRef = useRef(tests);
  testsRef.current = tests;
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    setIsLoading(true);
    setLoadError(null);
    Promise.all([
      fetchReviewQueue('pending'),
      fetchGeneratedTests()
    ])
      .then(([queueItems, generatedTests]) => {
        const testMap = new Map<string, string>();
        for (const gt of generatedTests) {
          testMap.set(gt.scenario_id, gt.code);
        }

        const mapped: TestItem[] = queueItems.map((item: ReviewQueueItem) => ({
          id: item.id,
          name: `${item.method} ${item.endpoint}`,
          path: '/' + (item.endpoint || '').replace(/^\//, ''),
          method: item.method || 'GET',
          confidence: item.confidence ?? 0.5,
          verdict: item.status === 'approved' ? 'approved' : 'review',
          gates: {
            syntax: true,
            structure: true,
            ast: true,
            novelty: true,
            dryRun: true,
            quality: item.review_gate_failed !== 'quality',
          },
          gateReasons: {
            quality: item.confidence_reason || item.review_gate_failed || 'Awaiting review.',
          },
          code: testMap.get(item.id) || `// Generated test for ${item.method} ${item.endpoint}\n`
        }));

        if (mapped.length > 0) {
          setTests(mapped);
          setSelectedTestId(mapped[0].id);
        }
        setIsLoading(false);
      })
      .catch(err => {
        toast('Failed to load review items from server.', 'error');
        setLoadError(err instanceof Error ? err.message : 'Failed to load review items.');
      })
      .finally(() => setIsLoading(false));
  }, []);
  const [activeFilter, setActiveFilter] = useState<'all' | 'approved' | 'review' | 'regenerating' | 'rejected'>('all');
  const [selectedTestId, setSelectedTestId] = useState<string>('test-3'); // Default to the first review item
  const [isEditing, setIsEditing] = useState(false);
  const [editedCode, setEditedCode] = useState('');
  const [approveTriggerId, setApproveTriggerId] = useState<string | null>(null);
  const [rejectingId, setRejectingId] = useState<string | null>(null);
  const [rejectReason, setRejectReason] = useState('');
  const [aiExplanation, setAiExplanation] = useState<string | null>(null);
  const [isExplaining, setIsExplaining] = useState(false);

  // Update pass rate on tests change
  useEffect(() => {
    const approvedCount = tests.filter(t => t.verdict === 'approved').length;
    onUpdatePassRateAndCount(tests.length, approvedCount);
  }, [tests, onUpdatePassRateAndCount]);

  // Sync edited code when selected test changes
  const activeTest = tests.find(t => t.id === selectedTestId) || tests[0];

  useEffect(() => {
    if (activeTest) {
      setEditedCode(activeTest.code);
      setIsEditing(false);
      setAiExplanation(null);
      setIsExplaining(false);
    }
  }, [selectedTestId]);

  // Keyboard Navigation & Actions
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Ignore if user is editing in textarea
      if (document.activeElement?.tagName === 'TEXTAREA' || document.activeElement?.tagName === 'INPUT') {
        return;
      }

      const visibleTests = tests.filter(t => {
        if (activeFilter === 'all') return true;
        return t.verdict === activeFilter;
      });

      const currentIndex = visibleTests.findIndex(t => t.id === selectedTestId);

      switch (e.key.toLowerCase()) {
        case 'j': // Next
          if (currentIndex < visibleTests.length - 1) {
            setSelectedTestId(visibleTests[currentIndex + 1].id);
          }
          break;
        case 'k': // Previous
          if (currentIndex > 0) {
            setSelectedTestId(visibleTests[currentIndex - 1].id);
          }
          break;
        case 'a': // Approve
          if (activeTest && activeTest.verdict !== 'approved') {
            handleApprove(activeTest.id);
          }
          break;
        case 'e': // Edit toggle
          setIsEditing(prev => !prev);
          break;
        case 'r': // Reject
          if (activeTest && activeTest.verdict !== 'rejected') {
            setRejectingId(activeTest.id);
            setRejectReason('');
          }
          break;
        default:
          break;
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [tests, selectedTestId, activeFilter, activeTest]);

  // Actions
  const handleApprove = async (id: string) => {
    setApproveTriggerId(id);

    try {
      await approveTestScenario(id);
      toast(`Approved test scenario ${id}`, 'success');
    } catch (err) {
      setApproveTriggerId(null);
      toast(`Failed to approve: ${(err as Error).message}`, 'error');
      return;
    }

    setTimeout(() => {
      setTests(prev => {
        const updated = prev.map(t => t.id === id ? { ...t, verdict: 'approved' as const } : t);
        setApproveTriggerId(null);
        const visible = updated.filter(t => activeFilter === 'all' || t.verdict === activeFilter);
        const idx = visible.findIndex(t => t.id === id);
        if (idx < visible.length - 1) {
          setSelectedTestId(visible[idx + 1].id);
        } else if (idx > 0) {
          setSelectedTestId(visible[idx - 1].id);
        }
        return updated;
      });
    }, 400);
  };

  const handleSaveEdit = async () => {
    try {
      await editTestScenario(selectedTestId, editedCode);
      toast('Edit saved successfully.', 'success');
    } catch (err) {
      toast(`Failed to save edit: ${(err as Error).message}`, 'error');
      return;
    }

    setTests(prev => prev.map(t => {
      if (t.id === selectedTestId) {
        return { 
          ...t, 
          code: editedCode,
          gates: { ...t.gates, quality: true },
          verdict: 'approved' 
        };
      }
      return t;
    }));
    setIsEditing(false);
  };

  const handleReject = async (id: string, reason: string) => {
    try {
      await rejectTestScenario(id, reason);
      toast(`Rejected ${id}. "${reason}"`, 'success');
    } catch (err) {
      toast(`Failed to reject: ${(err as Error).message}`, 'error');
      return;
    }

    setTests(prev => prev.map(t => {
      if (t.id === id) {
        return { 
          ...t, 
          verdict: 'rejected' as const,
          gates: { ...t.gates, quality: false } 
        };
      }
      return t;
    }));
    setRejectingId(null);
  };

  const handleExplain = async (id: string) => {
    setIsExplaining(true);
    try {
      const data = await explainTestScenario(id);
      setAiExplanation(data.explanation);
    } catch (err) {
      toast(`Failed to get AI explanation: ${(err as Error).message}`, 'error');
    } finally {
      setIsExplaining(false);
    }
  };

  const filteredTests = tests.filter(t => {
    if (activeFilter === 'all') return true;
    return t.verdict === activeFilter;
  });

  const getGateLabel = (gate: keyof TestGate) => {
    switch (gate) {
      case 'syntax': return 'SYN';
      case 'structure': return 'STR';
      case 'ast': return 'AST';
      case 'novelty': return 'NVL';
      case 'dryRun': return 'DRY';
      case 'quality': return 'QLT';
    }
  };

  return (
    <div className="p-6 h-full overflow-hidden flex flex-col justify-between grid-bg bg-transparent relative z-10" id="review-screen">
      
      {/* Page Header */}
      <div className="flex items-center justify-between border-b border-white/5 pb-4 shrink-0">
        <div className="flex items-center gap-4">
          <CherenkovLogo variant="icon" size={42} />
          <div>
            <h1 className="font-display font-semibold text-2xl text-text-primary tracking-tight">
              Human-In-The-Loop Validation Gate
            </h1>
            <p className="text-xs text-[#7D8DA1] mt-0.5">
              Audit high & low confidence tests. Approved tests are indexed as Playwright specs & positive learning vectors.
            </p>
          </div>
        </div>

        {/* Keyboard shortcut legend indicators */}
        <div className="hidden xl:flex items-center gap-3 text-[10px] font-mono text-[#7D8DA1] bg-white/5 border border-white/10 py-1.5 px-3 rounded-xl">
          <span className="text-glow-bright uppercase font-bold">Shortcuts:</span>
          <span className="flex items-center gap-1"><kbd className="bg-black/30 px-1 border border-white/10 text-text-primary rounded">J</kbd> / <kbd className="bg-black/30 px-1 border border-white/10 text-text-primary rounded">K</kbd> Navigate</span>
          <span>·</span>
          <span className="flex items-center gap-1"><kbd className="bg-black/30 px-1 border border-white/10 text-text-primary rounded flex items-center justify-center">A</kbd> Approve</span>
          <span>·</span>
          <span className="flex items-center gap-1"><kbd className="bg-black/30 px-1 border border-white/10 text-text-primary rounded">E</kbd> Edit</span>
          <span>·</span>
          <span className="flex items-center gap-1"><kbd className="bg-black/30 px-1 border border-white/10 text-text-primary rounded">R</kbd> Reset</span>
        </div>
      </div>

      {/* Main Two-Pane Split screen */}
      <div className="flex-1 overflow-hidden grid grid-cols-1 lg:grid-cols-5 gap-6 mt-6 items-stretch">
        
        {/* LEFT COLUMN: FILTER & QUEUE LIST PANEL (2/5 size) */}
        <div className="lg:col-span-2 flex flex-col bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl overflow-hidden h-full">
          {/* Tabs Filter Header */}
          <div className="flex border-b border-white/5 bg-black/40 p-2 gap-1 justify-between shrink-0 select-none">
            {(['all', 'approved', 'review', 'regenerating', 'rejected'] as const).map((filter) => {
              const count = filter === 'all' 
                ? tests.length 
                : tests.filter(t => t.verdict === filter).length;
              
              return (
                <button
                  key={filter}
                  onClick={() => setActiveFilter(filter)}
                  id={`filter-tab-${filter}`}
                  className={`flex-1 py-1.5 px-2 rounded font-mono text-[10px] uppercase font-bold truncate transition cursor-pointer text-center ${
                    activeFilter === filter
                      ? 'bg-[#131d31] text-glow-bright border border-white/10 font-semibold'
                      : 'text-[#7D8DA1] hover:text-text-primary hover:bg-white/5'
                  }`}
                >
                  <span className="block truncate">{filter}</span>
                  <span className="block text-[9px] text-[#7D8DA1]/70 font-normal mt-0.5 font-sans">({count})</span>
                </button>
              );
            })}
          </div>

          {/* Test items lists */}
          <div className="flex-1 overflow-y-auto divide-y divide-white/5 p-4 space-y-2.5">
            {isLoading ? (
              <div className="h-full flex flex-col items-center justify-center text-center font-sans space-y-1.5 py-24">
                <Skeleton className="w-10 h-10 rounded-full" />
                <p className="text-text-muted text-xs font-semibold">Loading review queue...</p>
                <p className="text-[11px] text-text-muted/60">Fetching from backend.</p>
              </div>
            ) : loadError ? (
              <div className="h-full flex flex-col items-center justify-center text-center font-sans space-y-1.5 py-24">
                <AlertTriangle className="w-12 h-12 text-amber-400" />
                <p className="text-text-muted text-xs font-semibold">Failed to load review items</p>
                <p className="text-[11px] text-text-muted/60">{loadError}</p>
              </div>
            ) : filteredTests.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center text-center font-sans space-y-1.5 py-24">
                <FolderCheck className="w-12 h-12 text-[#7D8DA1] animate-pulse font-bold" />
                <p className="text-text-muted text-xs font-semibold">No tests match this audit filter</p>
                <p className="text-[11px] text-text-muted/60">Generate more endpoints to populate queues</p>
              </div>
            ) : (
              filteredTests.map((test) => {
                const isSelected = selectedTestId === test.id;
                const isApproved = test.verdict === 'approved';
                const isReview = test.verdict === 'review';
                const isRegenerating = test.verdict === 'regenerating';
                
                return (
                  <div
                    key={test.id}
                    id={`test-row-${test.id}`}
                    onClick={() => setSelectedTestId(test.id)}
                    className={`p-3 rounded-xl border cursor-pointer transition-all duration-300 relative ${
                      isSelected 
                        ? 'bg-white/10 border-glow-blue shadow-lg shadow-cyan-500/5'
                        : 'bg-black/20 border-white/5 hover:border-border-custom hover:bg-white/5'
                    } ${isReview ? 'border-l-2 border-l-amber-500' : ''} ${
                      approveTriggerId === test.id ? 'bg-[#3FB950]/15 border-[#3FB950] transition-transform duration-300 scale-[0.98]' : ''
                    }`}
                  >
                    {/* Confidence Meter and Badging row */}
                    <div className="flex justify-between items-start">
                      <div className="max-w-[75%]">
                        <span className="block text-[10px] font-mono text-[#7D8DA1] font-semibold">{test.method} {test.path}</span>
                        <h4 className="text-xs font-semibold text-text-primary mt-1 truncate">{test.name}</h4>
                      </div>

                      {/* Verdict Badge */}
                      <span className={`px-2 py-0.5 rounded text-[8px] font-mono font-bold tracking-wider uppercase border ${
                        isApproved ? 'bg-[#3FB950]/10 text-[#3FB950] border-[#3FB950]/30' :
                        isReview ? 'bg-[#D29922]/10 text-[#D29922] border-[#D29922]/30' :
                        'bg-glow-blue/10 text-glow-bright border-[#2D9CDB]/30 animate-pulse'
                      }`}>
                        {test.verdict}
                      </span>
                    </div>

                    {/* Confidence percentage and bar */}
                    <div className="mt-3 flex items-center justify-between gap-4 font-mono text-[10px]">
                      <div className="flex-1 flex items-center gap-2">
                        <span className="text-[#7D8DA1]">CONF:</span>
                        <div className="flex-1 bg-black/30 h-1.5 rounded-full overflow-hidden border border-white/5">
                          <div className="bg-glow-blue h-full" style={{ width: `${test.confidence * 100}%` }} />
                        </div>
                      </div>
                      <span className="text-glow-bright font-bold">{(test.confidence * 100).toFixed(0)}%</span>
                    </div>

                    {/* Miniature Gate Status Indicators */}
                    <div className="flex items-center justify-between mt-3 pt-2.5 border-t border-white/5">
                      <div className="flex items-center gap-1.5">
                        <span className="text-[9px] font-mono font-bold text-text-muted">GATES:</span>
                        <div className="flex items-center gap-1 text-[8px] font-mono">
                          {(Object.keys(test.gates) as Array<keyof TestGate>).map((gate) => {
                            const isGateOK = test.gates[gate];
                            return (
                              <span
                                key={gate}
                                title={`${gate}: ${isGateOK ? 'Pass' : 'Warning/Failed'}`}
                                className={`px-1 rounded-[2px] font-bold border ${
                                  isGateOK 
                                    ? 'bg-[#3FB950]/10 text-[#3FB950] border-[#3FB950]/35' 
                                    : 'bg-[#D29922]/10 text-amber-400 border-amber-500/20 animate-pulse'
                                }`}
                              >
                                {getGateLabel(gate)}
                              </span>
                            );
                          })}
                        </div>
                      </div>

                      {/* Run duration stats */}
                      {test.actualResult && (
                        <div className="flex items-center gap-1 text-[9px] font-mono text-[#7D8DA1]">
                           <Clock className="w-2.5 h-2.5" />
                          <span>{test.actualResult.duration}</span>
                        </div>
                      )}
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* RIGHT COLUMN: CODE REVIEW & DETAILS SUB-PANEL (3/5 size) */}
        <div className="lg:col-span-3 flex flex-col bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl overflow-hidden h-full">
          {activeTest ? (
            <div className="h-full flex flex-col justify-between">
              
              {/* Review Test Header info */}
              <div className="p-4 bg-black/40 border-b border-white/5 shrink-0">
                <div className="flex items-center justify-between text-xs">
                  <div>
                    <h3 className="font-display font-semibold text-sm text-text-primary">{activeTest.name}</h3>
                    <p className="text-[11px] font-mono text-[#7D8DA1] mt-0.5">PLAYWRIGHT COMPONENT SPEC · PATH: {activeTest.path}</p>
                  </div>

                  <div className="text-right">
                    <span className="block text-[10px] font-mono uppercase text-[#7D8DA1]">Confidence metrics</span>
                    <span className="text-base font-bold text-glow-bright font-mono">{activeTest.confidence * 100}%</span>
                  </div>
                </div>
              </div>

              {/* Middle View: Test editor viewport */}
              <div className="flex-1 p-4 overflow-y-auto space-y-4">
                
                {/* Visual Code Editor Field */}
                <div className="bg-black/30 border border-white/10 rounded-xl overflow-hidden flex flex-col">
                  <div className="flex items-center justify-between p-2 px-3 bg-white/5 border-b border-white/5">
                    <div className="flex items-center gap-2">
                      <Code className="w-3.5 h-3.5 text-glow-blue" />
                      <span className="text-[10px] font-mono text-text-muted">tsconfig-ast.spec.ts</span>
                    </div>
                    {isEditing ? (
                      <span className="text-[9px] font-mono px-2 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20 animate-pulse">
                        EDIT MODE ACTIVE
                      </span>
                    ) : (
                      <span className="text-[9px] font-mono text-[#7D8DA1]">Syntax Verified by tsc v5.8</span>
                    )}
                  </div>

                  {isEditing ? (
                    <textarea
                      id="review-inline-editor"
                      value={editedCode}
                      onChange={(e) => setEditedCode(e.target.value)}
                      className="w-full h-64 p-4 font-mono text-xs text-[#E6EDF3] bg-black/30 focus:outline-none resize-none leading-relaxed overflow-y-auto"
                    />
                  ) : (
                    <div className="p-4 font-mono text-xs text-[#E6EDF3] leading-relaxed bg-black/30 overflow-x-auto overflow-y-auto max-h-72">
                      <pre><code>{activeTest.code}</code></pre>
                    </div>
                  )}
                </div>

                {/* Gate Audit Breakdown Explanation list */}
                <div className="space-y-2">
                  <h4 className="text-[10px] font-mono uppercase tracking-wider text-text-muted">Pipeline check details explanation</h4>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    
                    {/* Gate 1: semantic quality error explanation */}
                    <div className="p-3 rounded-xl border border-white/5 bg-white/5 space-y-1.5">
                      <div className="flex items-center gap-1.5">
                        <CheckCircle className={`w-3.5 h-3.5 ${activeTest.gates.quality ? 'text-[#3FB950]' : 'text-[#D29922]'}`} />
                        <span className="font-mono text-[10px] font-bold text-text-primary uppercase">Assertion Quality</span>
                      </div>
                      <p className="text-[11px] text-[#7D8DA1]/85 leading-relaxed font-sans">
                        {activeTest.gateReasons.quality || 'Assertions fully map to status codes and sub-keys listed in spec examples.'}
                      </p>
                    </div>

                    {/* Gate 2: ast verification */}
                    <div className="p-3 rounded-xl border border-white/5 bg-white/5 space-y-1.5">
                      <div className="flex items-center gap-1.5">
                        <CheckCircle className={`w-3.5 h-3.5 ${activeTest.gates.ast ? 'text-[#3FB950]' : 'text-[#D29922]'}`} />
                        <span className="font-mono text-[10px] font-bold text-text-primary uppercase">AST validation</span>
                      </div>
                      <p className="text-[11px] text-[#7D8DA1]/85 leading-relaxed font-sans">
                        {activeTest.gateReasons.ast || 'Syntax structure complies with ESM module imports and Playwright test callbacks.'}
                      </p>
                    </div>

                  </div>
                </div>

                {/* Dry Run Console trace */}
                {activeTest.actualResult && (
                  <div className="bg-white/5 border border-white/10 rounded-xl p-3.5 font-mono text-[11px] space-y-2">
                    <div className="flex justify-between items-center text-[10px]">
                      <span className="text-[#7D8DA1]">LOCAL SERVER DRY-RUN STREAM OUTPUT</span>
                      <span className={`px-2 py-0.5 rounded text-[9px] uppercase font-bold border ${
                        activeTest.actualResult.status === 'passed'
                          ? 'bg-[#3FB950]/10 text-[#3FB950] border-[#3FB950]/30'
                          : 'bg-[#F85149]/10 text-red-400 border-red-500/20'
                      }`}>
                        {activeTest.actualResult.status}
                      </span>
                    </div>
                    <pre className="p-2.5 rounded-xl bg-black/35 border border-white/5 text-[#7D8DA1]/90 max-h-24 overflow-y-auto leading-relaxed whitespace-pre-wrap">
                      {activeTest.actualResult.stdout}
                    </pre>
                  </div>
                )}
                
                {/* AI Explanation Area */}
                {(activeTest.verdict === 'review' || aiExplanation) && (
                  <div className="bg-glow-blue/5 border border-glow-blue/20 rounded-xl p-4 space-y-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Sparkles className="w-4 h-4 text-glow-blue" />
                        <h4 className="text-[10px] font-mono uppercase tracking-wider text-glow-bright font-bold">Ask Copilot</h4>
                      </div>
                      {!aiExplanation && (
                        <button
                          onClick={() => handleExplain(activeTest.id)}
                          disabled={isExplaining}
                          className="px-3 py-1 bg-glow-blue/10 hover:bg-glow-blue/20 text-glow-bright border border-glow-blue/30 rounded text-[9px] font-mono font-bold uppercase transition disabled:opacity-50"
                        >
                          {isExplaining ? 'ANALYZING...' : 'EXPLAIN FLAGGED STATUS'}
                        </button>
                      )}
                    </div>
                    {aiExplanation && (
                      <div className="text-xs text-[#E6EDF3] leading-relaxed font-sans bg-black/20 p-3 rounded-lg border border-white/5">
                        {aiExplanation}
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* Bottom Sticky Action Bar Drawer */}
              <div className="p-4 bg-black/40 border-t border-white/5 flex items-center justify-between gap-4 shrink-0">
                {isEditing ? (
                  <>
                    <button
                      onClick={() => setIsEditing(false)}
                      className="px-4 py-2 border border-white/10 text-[#7D8DA1] rounded-xl text-xs font-mono hover:text-[#E6EDF3] hover:bg-white/5 transition cursor-pointer"
                    >
                      CANCEL EDIT
                    </button>
                    <button
                      onClick={handleSaveEdit}
                      className="px-6 py-2 bg-glow-blue hover:bg-opacity-95 text-slate-950 font-bold rounded-xl text-xs tracking-wider uppercase font-mono transition shadow-md cursor-pointer"
                    >
                      SAVE CHANGE & INGEST DIRECTORY
                    </button>
                  </>
                ) : (
                  <>
                    <div className="flex gap-2">
                      <button
                        onClick={() => setRejectingId(activeTest.id)}
                        className="px-4 py-2 text-red-400 border border-red-500/20 bg-red-500/5 hover:bg-red-500 hover:text-slate-950 text-xs font-mono font-bold tracking-wider rounded-xl uppercase transition cursor-pointer"
                      >
                        REJECT & RUN REGEN
                      </button>
                      <button
                        onClick={() => setIsEditing(true)}
                        className="px-4 py-2 text-[#7D8DA1] hover:text-glow-bright border border-white/10 hover:border-glow-blue text-xs font-mono rounded-xl uppercase transition cursor-pointer"
                      >
                        EDIT INLINE CODE
                      </button>
                    </div>

                    <button
                      onClick={() => handleApprove(activeTest.id)}
                      className="px-8 py-2 bg-[#3FB950] hover:bg-opacity-95 text-[#FFFFFF] font-bold rounded-xl text-xs tracking-wider uppercase font-mono transition-all duration-300 shadow-lg cursor-pointer"
                    >
                      APPROVE SPEC TEST
                    </button>
                  </>
                )}
              </div>

            </div>
          ) : (
            <div className="h-full flex items-center justify-center p-8 text-center text-text-muted">
              Select an item on the left index trace to verify code schema.
            </div>
          )}
        </div>

      </div>

      {/* Rejection Reason Modal */}
      {rejectingId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm animate-fadeIn">
          <div className="bg-[#131d31] border border-white/10 p-6 rounded-2xl w-full max-w-md shadow-2xl space-y-4">
            <h3 className="text-sm font-semibold font-mono uppercase tracking-wider text-text-muted">
              Specify Rejection Reason (Feeds Reflector)
            </h3>
            <p className="text-xs text-[#7D8DA1]">
              Provide instructions to guide the model rewrite and update negative verdict weights.
            </p>
            <textarea
              value={rejectReason}
              onChange={(e) => setRejectReason(e.target.value)}
              placeholder="e.g. Assertion values are hardcoded incorrectly. Must verify dynamic IDs..."
              className="w-full h-24 p-3 font-sans text-xs text-[#E6EDF3] bg-black/30 border border-white/10 rounded-xl focus:outline-none focus:border-glow-blue transition"
            />
            <div className="flex justify-end gap-3 text-xs">
              <button
                onClick={() => setRejectingId(null)}
                className="px-4 py-2 border border-white/10 text-[#7D8DA1] rounded-xl font-mono hover:text-[#E6EDF3] hover:bg-white/5 transition"
              >
                CANCEL
              </button>
              <button
                onClick={() => handleReject(rejectingId, rejectReason || 'Rejected by reviewer')}
                className="px-4 py-2 bg-red-500 hover:bg-opacity-95 text-slate-950 font-bold rounded-xl font-mono uppercase transition"
              >
                CONFIRM REJECT
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
