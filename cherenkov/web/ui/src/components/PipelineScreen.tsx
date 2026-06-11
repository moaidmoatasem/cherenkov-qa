/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect, useRef } from 'react';
import { 
  Play, 
  Pause, 
  Cpu, 
  Database, 
  CheckCircle, 
  Zap, 
  Terminal, 
  ChevronRight, 
  X,
  Compass,
  Code,
  AlertTriangle
} from 'lucide-react';
import { PipelineStage, StageId } from '../types';

import CherenkovLogo from './CherenkovLogo';
import { useLiveEvents } from '../hooks/useLiveEvents';

interface PipelineScreenProps {
  onCompletePipeline: () => void;
  onUpdateTokensSpent: (tokens: number, cost: number) => void;
}

export default function PipelineScreen({ 
  onCompletePipeline,
  onUpdateTokensSpent 
}: PipelineScreenProps) {
  const { lastEvent, connected } = useLiveEvents();
  
  // Pipeline steps state
  const [stages, setStages] = useState<PipelineStage[]>([
    { id: 'ingest', name: 'INGEST', status: 'done', summary: '20 endpoints indexed' },
    { id: 'plan', name: 'PLAN', status: 'done', summary: 'Contract & validation plans complete' },
    { id: 'generate', name: 'GENERATE', status: 'running', summary: 'Synthesizing Playwright specs' },
    { id: 'review', name: 'REVIEW', status: 'queued', summary: 'HITL checklist pending' },
    { id: 'visual', name: 'VISUAL E2E', status: 'queued', summary: 'UI screenshot verification' },
    { id: 'perf', name: 'PERFORMANCE', status: 'queued', summary: 'Statistical latency analysis' }
  ]);

  const [activeStageId, setActiveStageId] = useState<StageId>('generate');
  const [isPaused, setIsPaused] = useState(false);
  const [elapsedTime, setElapsedTime] = useState(138); // starts at 2:18
  
  // Telemetry details state
  const [tokensSpent, setTokensSpent] = useState(11243);
  const [contextTokens, setContextTokens] = useState(14200); // starts past 40%
  const [shownDrawerId, setShownDrawerId] = useState<StageId | null>(null);

  // Streaming text indices
  const [currentTestIndex, setCurrentTestIndex] = useState(0);
  const [typedCode, setTypedCode] = useState('');
  const [completedTests, setCompletedTests] = useState<string[]>([
    'GET /user/login · checks auth cookie parameter values',
    'POST /user · creates standard user entity'
  ]);

  // Real-time Event Queue from Websocket
  const [realTestQueue, setRealTestQueue] = useState<Array<{ endpoint: string, code: string, agent: string }>>([]);

  // Timers references
  const elapsedTimerRef = useRef<NodeJS.Timeout | null>(null);
  const typingTimerRef = useRef<NodeJS.Timeout | null>(null);
  const charIndexRef = useRef(0);

  // Parse WS events
  useEffect(() => {
    if (!lastEvent) return;
    
    const { type, payload } = lastEvent;
    
    if (type === 'stage_start') {
      const { stage } = payload;
      setStages(prev => prev.map(s => {
        if (s.id === stage.toLowerCase()) return { ...s, status: 'running', summary: 'Stage execution active' };
        if (s.id === 'ingest' && stage === 'PLAN') return { ...s, status: 'done' };
        if (s.id === 'plan' && stage === 'GENERATE') return { ...s, status: 'done' };
        if (s.id === 'generate' && stage === 'REVIEW') return { ...s, status: 'done' };
        if (s.id === 'review' && stage === 'VISUAL') return { ...s, status: 'done' };
        if (s.id === 'visual' && stage === 'PERF') return { ...s, status: 'done' };
        return s;
      }));
      setActiveStageId(stage.toLowerCase() as StageId);
    }
    
    else if (type === 'stage_success') {
      const { stage, summary } = payload;
      setStages(prev => prev.map(s => {
        if (s.id === stage.toLowerCase()) return { ...s, status: 'done', summary };
        return s;
      }));
    }
    
    else if (type === 'test_generated') {
      const { endpoint, method, code, agent } = payload;
      setRealTestQueue(prev => [...prev, { endpoint: `${method} ${endpoint}`, code, agent }]);
    }
    
    else if (type === 'pipeline_complete') {
      setTimeout(() => {
        onCompletePipeline();
      }, 2000);
    }
  }, [lastEvent]);

  // Keep track of current test object (real queue gets priority)
  const currentTest = realTestQueue.length > 0 && currentTestIndex < realTestQueue.length
    ? realTestQueue[currentTestIndex]
    : { endpoint: 'Waiting for stream...', code: '', agent: 'System' };

  // 1. Elapsed timer
  useEffect(() => {
    if (!isPaused) {
      elapsedTimerRef.current = setInterval(() => {
        setElapsedTime(prev => prev + 1);
      }, 1000);
    } else {
      if (elapsedTimerRef.current) clearInterval(elapsedTimerRef.current);
    }

    return () => {
      if (elapsedTimerRef.current) clearInterval(elapsedTimerRef.current);
    };
  }, [isPaused]);

  // 2. Character-by-character typing stream simulation
  useEffect(() => {
    if (isPaused) {
      if (typingTimerRef.current) clearInterval(typingTimerRef.current);
      return;
    }

    if (!currentTest) return;

    const fullCode = currentTest.code;
    charIndexRef.current = 0;
    setTypedCode('');

    typingTimerRef.current = setInterval(() => {
      if (charIndexRef.current < fullCode.length) {
        const step = Math.min(3, fullCode.length - charIndexRef.current);
        const nextChars = fullCode.substring(charIndexRef.current, charIndexRef.current + step);
        
        setTypedCode(prev => prev + nextChars);
        charIndexRef.current += step;

        const addedTokens = Math.round(step * 1.4);
        setTokensSpent(prev => prev + addedTokens);

        setContextTokens(prev => {
          const added = Math.round(step * 0.95);
          return Math.min(32768, prev + added);
        });

      } else {
        clearInterval(typingTimerRef.current!);
        
        setCompletedTests(prev => [...prev, `${currentTest.endpoint} · fully compiled ✓`]);

        const limit = realTestQueue.length > 0 ? realTestQueue.length : 1;

        setTimeout(() => {
          if (currentTestIndex < limit - 1) {
            setCurrentTestIndex(prev => prev + 1);
          } else if (realTestQueue.length === 0) {
            // Simulated only fallback complete
            setStages(prev => prev.map(s => {
              if (s.id === 'generate') return { ...s, status: 'done', summary: 'All suites compiled successfully' };
              if (s.id === 'review') return { ...s, status: 'running', summary: 'Awaiting human authorization gate' };
              return s;
            }));
            setActiveStageId('review');
            
            setTimeout(() => {
              onCompletePipeline();
            }, 3000);
          }
        }, 1500);
      }
    }, 25);

    return () => {
      if (typingTimerRef.current) clearInterval(typingTimerRef.current);
    };
  }, [currentTestIndex, isPaused, realTestQueue, currentTest]);

  // Synchronize token usage with parent state
  useEffect(() => {
    onUpdateTokensSpent(tokensSpent, tokensSpent * 0.000002);
  }, [tokensSpent]);

  // format time
  const formatTime = (timeInSecs: number) => {
    const mins = Math.floor(timeInSecs / 60);
    const secs = timeInSecs % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  const handleCompactContext = () => {
    // clean semantic compaction, reduce context to optimize prompt attention
    setContextTokens(prev => Math.round(prev * 0.5));
  };

  const contextPercent = Math.min(100, Math.round((contextTokens / 32768) * 100));

  return (
    <div className="p-6 h-full overflow-y-auto space-y-6 grid-bg bg-transparent relative z-10 flex flex-col justify-between" id="pipeline-screen" data-testid="pipeline-screen">
      
      {/* Upper Panel header controls */}
      <div className="flex items-center justify-between border-b border-white/10 pb-4">
        <div className="flex items-center gap-4">
          <CherenkovLogo variant="icon" size={42} />
          <div>
            <h1 className="font-display font-semibold text-2xl text-text-primary tracking-tight">
              AI Code Generation Pipeline
            </h1>
            <p className="text-xs text-[#7D8DA1] mt-0.5 font-sans">
              Observe the active state models synthesize API validation tests from OpenAPI paths.
            </p>
          </div>
        </div>

        {/* Controls */}
        <div className="flex items-center gap-3">
          <div className="text-xs font-mono px-3 py-1 bg-white/5 border border-white/10 rounded flex items-center gap-2">
            <span className="text-text-muted">ELAPSED:</span>
            <span className="text-glow-bright font-semibold">{formatTime(elapsedTime)}</span>
          </div>

          <button
            onClick={() => setIsPaused(!isPaused)}
            id="pipeline-pause-resume-btn"
            data-testid="pipeline-run-btn"
            className="flex items-center gap-1.5 px-4.5 py-1.5 rounded bg-white/5 border border-white/10 hover:border-glow-blue text-[#E6EDF3] text-xs font-mono transition duration-200 cursor-pointer"
          >
            {isPaused ? (
              <>
                <Play className="w-3.5 h-3.5 text-success-custom fill-success-custom" />
                <span>RESUME PIPELINE</span>
              </>
            ) : (
              <>
                <Pause className="w-3.5 h-3.5 text-warning-custom fill-warning-custom" />
                <span>PAUSE PIPELINE</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* REGION A - THE PIPELINE (HORIZONTAL 4-NODE DAG) */}
      <div className="bg-white/5 backdrop-blur-xl border border-white/10 p-5 rounded-2xl">
        <h2 className="text-[10px] font-mono tracking-widest text-[#7D8DA1] uppercase mb-4">AST TRANSLATION pipeline structure</h2>
        
        <div className="flex flex-col md:flex-row items-center justify-between gap-2 relative">
          
          {stages.map((stage, idx) => {
            const isRunning = stage.status === 'running';
            const isDone = stage.status === 'done';
            
            return (
              <React.Fragment key={stage.id}>
                {/* Node Box */}
                <div
                  id={`pipeline-node-${stage.id}`}
                  onClick={() => setShownDrawerId(stage.id)}
                  className={`flex-1 w-full md:w-auto p-4 rounded-xl border transition-all duration-300 cursor-pointer relative select-none ${
                    isRunning 
                      ? 'bg-white/10 border-glow-blue cherenkov-glow shadow-md shadow-cyan-500/10' 
                      : isDone 
                        ? 'bg-white/5 border-white/10 hover:bg-white/10' 
                        : 'bg-black/10 border-white/5 opacity-60'
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <span className="block text-[10px] font-mono text-[#7D8DA1]/85 font-semibold tracking-wider">{stage.name}</span>
                      <h4 className="text-sm font-semibold text-text-primary mt-1">{stage.id === 'generate' && !isPaused ? `Synthesizing ${currentTest.endpoint}` : stage.summary}</h4>
                    </div>
                    {/* Status Dot */}
                    <span className="relative flex h-2.5 w-2.5 mt-1" data-testid={`pipeline-status-${stage.id}`} data-status={stage.status}>
                      {isRunning && (
                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-glow-blue opacity-85"></span>
                      )}
                      <span className={`relative inline-flex rounded-full h-2.5 w-2.5 ${
                        isDone ? 'bg-[#3FB950]' : isRunning ? 'bg-glow-bright' : 'bg-gray-brand'
                      }`} />
                    </span>
                  </div>
                  
                  <div className="mt-3 flex items-center justify-between text-[10px] font-mono text-[#7D8DA1]">
                    <span>STAGE {idx + 1}/4</span>
                    <span className="text-glow-bright hover:underline">DRT Trace</span>
                  </div>
                </div>

                {/* Connecting Line Beam between Nodes */}
                {idx < stages.length - 1 && (
                  <div className="hidden md:block w-8 h-[2px] bg-[#233044] relative overflow-hidden shrink-0">
                    {/* Flowing particle animation if previous done and current is running */}
                    {isDone && stages[idx + 1].status === 'running' && (
                      <div className="absolute top-0 left-0 w-4 h-full bg-[#5BC0F8] rounded-full blur-[1px] animate-beam-flow" style={{
                        animation: 'beam-flow 1s linear infinite'
                      }} />
                    )}
                  </div>
                )}
              </React.Fragment>
            );
          })}
        </div>
      </div>

      {/* LOWER STACK - MONOSPACE STREAM PANEL AND TELEMETRY GRID */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-stretch">
        
        {/* REGION B: LIVE MONOSPACE STREAM CODE PANEL (COL-SPAN 2) */}
        <div className="lg:col-span-2 flex flex-col bg-black/40 backdrop-blur-xl border border-white/10 rounded-2xl overflow-hidden min-h-[380px] h-[440px] relative">
          
          {!connected && (
            <div className="absolute inset-0 bg-black/80 backdrop-blur-md flex flex-col items-center justify-center z-10 text-center space-y-3">
              <AlertTriangle className="w-10 h-10 text-amber-500 animate-pulse" />
              <div className="text-text-primary font-semibold text-sm">Connection Lost or Initializing</div>
              <p className="text-xs text-[#7D8DA1] max-w-sm">Waiting for live generator socket. If this persists, verify the backend is running.</p>
            </div>
          )}

          {/* Editor Header panel */}
          <div className="flex items-center justify-between bg-white/5 border-b border-white/10 px-4 py-3 shrink-0">
            <div className="flex items-center gap-2">
              <Terminal className="w-4 h-4 text-glow-bright" />
              <span className="text-xs font-mono text-text-primary font-bold">{currentTest.agent}</span>
              <span className="text-[#334C5A]">|</span>
              <span className="text-xs font-mono text-glow-blue">compiling {currentTest.endpoint}</span>
            </div>
            
            {/* Blinking State marker */}
            <div className="flex items-center gap-1.5 font-mono text-[10px] text-text-muted">
              <span className="w-1.5 h-1.5 rounded-full bg-glow-blue animate-ping" />
              <span>STREAMING ACTIVE</span>
            </div>
          </div>

          {/* Completed stack above writing screen */}
          {completedTests.length > 0 && (
            <div className="bg-black/25 border-b border-white/10 px-4 py-2 flex flex-col gap-1 overflow-y-auto max-h-[85px] scrollbar-thin">
              {completedTests.map((t, idx) => (
                <div key={idx} className="flex items-center gap-2 text-[11px] font-mono text-[#3FB950] animate-fadeIn">
                  <CheckCircle className="w-3 h-3 shrink-0" />
                  <span>{t}</span>
                </div>
              ))}
            </div>
          )}

          {/* Typing Stream Canvas */}
          <div className="flex-1 p-4 overflow-y-auto font-mono text-xs text-[#E6EDF3] leading-relaxed select-text bg-black/10">
            <pre className="whitespace-pre-wrap word-break">
              <code>
                {typedCode}
                <span className="inline-block w-1.5 h-4 bg-glow-bright animate-pulse ml-0.5 align-middle" />
              </code>
            </pre>
          </div>
        </div>

        {/* REGION C: TELEMETRY METRIC READOUT PANEL */}
        <div className="bg-white/5 backdrop-blur-xl border border-white/10 p-5 rounded-2xl flex flex-col justify-between space-y-6">
          <div className="space-y-6">
            <h3 className="text-xs font-mono uppercase tracking-wider text-text-muted border-b border-white/10 pb-2">Active Telemetry</h3>
            
            {/* Tokens metrics */}
            <div className="space-y-2">
              <div className="flex justify-between text-xs font-mono">
                <span className="text-[#7D8DA1]">TOKEN BUDGET</span>
                <span className="text-text-primary">{tokensSpent.toLocaleString()} / 50,000</span>
              </div>
              <div className="w-full bg-black/40 h-2 rounded-full border border-white/10" data-testid="pipeline-progress">
                <div className="bg-glow-blue rounded-full h-full" style={{ width: `${(tokensSpent / 50000) * 100}%` }} />
              </div>
              <div className="flex justify-between text-[11px] font-mono text-[#7D8DA1]">
                <span>Plan: {(tokensSpent * 0.22).toFixed(0)}</span>
                <span>Generate: {(tokensSpent * 0.78).toFixed(0)}</span>
              </div>
            </div>

            {/* Context metrics */}
            <div className="space-y-2">
              <div className="flex justify-between items-center text-xs font-mono">
                <span className="text-[#7D8DA1]">PROMPT ATTENTION SPACE</span>
                <div className="flex items-center gap-2">
                  <span className={contextPercent > 50 ? 'text-[#D29922]' : 'text-glow-bright'}>{contextPercent}%</span>
                  {contextPercent > 50 && (
                    <button
                      onClick={handleCompactContext}
                      className="px-1.5 py-0.5 rounded bg-[#D29922]/15 text-[#D29922] border border-[#D29922]/40 hover:bg-[#D29922] hover:text-bg-base text-[9px] animate-pulse transition duration-200"
                    >
                      [COMPACT]
                    </button>
                  )}
                </div>
              </div>
              <div className="w-full bg-black/40 h-2 rounded-full border border-white/10">
                <div className={`rounded-full h-full transition-all duration-300 ${
                  contextPercent > 50 ? 'bg-[#D29922]' : 'bg-glow-blue'
                }`} style={{ width: `${contextPercent}%` }} />
              </div>
              <div className="text-[10px] text-text-muted leading-tight font-mono">
                {contextTokens.toLocaleString()} / 32,768 Context vector spaces occupied. Compaction trims redundancies to bypass limits.
              </div>
            </div>

            {/* Live estimated cost simulation */}
            <div className="p-3.5 bg-black/30 border border-white/10 rounded-xl space-y-1 font-mono text-[11px]">
              <span className="block text-[#7D8DA1] uppercase text-[10px]">CURRENT EXPENDITURE</span>
              <div className="flex justify-between text-text-primary text-xs mt-1">
                <span>Local model execution cost:</span>
                <span className="text-[#3FB950] font-sans font-bold">$0.00 local</span>
              </div>
              <div className="flex justify-between text-[#7D8DA1] mt-0.5">
                <span>Equivalent Cloud Cost:</span>
                <span className="text-glow-bright font-sans font-semibold">${(tokensSpent * 0.000018).toFixed(4)} USD</span>
              </div>
            </div>
          </div>

          {/* Scenario tag footer */}
          <div className="bg-white/5 p-3 rounded-xl border border-white/5 font-mono text-[10px] space-y-1 select-none">
            <div className="flex items-center gap-1.5 text-glow-bright">
              <Compass className="w-3.5 h-3.5 text-glow-blue" />
              <span>CURRENT SCENARIO:</span>
            </div>
            <p className="text-[#7D8DA1] text-[11px] truncate mt-0.5">authorization_expiry_check, json_syntax_validation</p>
          </div>
        </div>
      </div>

      {/* Stage Detail Drawer Modal */}
      {shownDrawerId && (
        <div className="fixed inset-0 bg-black/40 backdrop-blur-md z-50 flex items-center justify-center p-4">
          <div className="bg-[#131d31] backdrop-blur-2xl border border-white/10 rounded-2xl w-full max-w-lg p-6 relative shadow-2xl">
            <button
              onClick={() => setShownDrawerId(null)}
              className="absolute top-4 right-4 text-[#7D8DA1] hover:text-[#E6EDF3] p-1 rounded"
            >
              <X className="w-5 h-5" />
            </button>
            
            <h3 className="font-display font-bold text-lg text-text-primary uppercase tracking-wider mb-2">
              Stage Diagnostics: {shownDrawerId}
            </h3>
            
            <div className="space-y-4 text-xs font-sans mt-4">
              <div className="p-3 bg-black/40 rounded-xl border border-white/10 font-mono text-[#7D8DA1]">
                Status code: <span className="text-glow-bright font-bold uppercase">SECURED_200</span><br />
                Process ID: <span className="text-text-primary">02_Rad_X_{shownDrawerId}</span>
              </div>

              <div className="space-y-1 leading-relaxed text-[#7D8DA1]">
                <h4 className="text-text-primary text-xs font-semibold uppercase font-mono">Overview details</h4>
                <p>
                  At this stage of the test suite generation, Cherenkov validates input schema constraints, resolves structural parameter mapping, and outputs robust, typed tests without leaving local memory.
                </p>
              </div>

              <div className="pt-2 flex justify-end">
                <button
                  type="button"
                  onClick={() => setShownDrawerId(null)}
                  className="px-4 py-1.5 bg-white/5 hover:bg-glow-blue hover:text-slate-950 rounded-xl font-mono text-xs font-semibold text-text-primary border border-white/10 transition"
                >
                  DISMISS DIAGNOSTIC
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
