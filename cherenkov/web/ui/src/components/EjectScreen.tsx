/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState } from 'react';
import { 
  Download, 
  Folder, 
  FileCode, 
  ChevronRight, 
  ChevronDown, 
  CheckCircle, 
  Copy, 
  Share2, 
  HardDrive,
  Cpu,
  AlertCircle
} from 'lucide-react';

import { ejectSuite } from '../lib/api';
import CherenkovLogo from './CherenkovLogo';
import { useToast } from './ui/Toast';

export default function EjectScreen() {
  const [outputPath, setOutputPath] = useState('./playwright-suite');
  const [isEjected, setIsEjected] = useState(false);
  const [ejectError, setEjectError] = useState<string | null>(null);
  const [copySuccess, setCopySuccess] = useState(false);
  const [expandedNodes, setExpandedNodes] = useState<{ [key: string]: boolean }>({
    'playwright-suite': true,
    'playwright-suite/tests': true,
    'playwright-suite/clients': true,
  });
  const { toast } = useToast();

  const runCommandText = `cd playwright-suite && npm install && npx playwright test`;

  const toggleNode = (nodePath: string) => {
    setExpandedNodes(prev => ({
      ...prev,
      [nodePath]: !prev[nodePath]
    }));
  };

  const handleEject = async () => {
    setEjectError(null);
    try {
      const res = await ejectSuite(outputPath);
      if (res.status === 'error' || res.status === 'failed') {
        throw new Error(res.status || 'Unknown backend error');
      }
      setIsEjected(true);
      toast('Eject successful — files written to ' + outputPath, 'success');
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      setEjectError(msg);
      toast(`Eject failed: ${msg}`, 'danger');
    }
  };

  const handleCopy = () => {
    navigator.clipboard.writeText(runCommandText);
    setCopySuccess(true);
    setTimeout(() => setCopySuccess(false), 2000);
  };

  // recursive file tree renderer helper
  const renderTree = (node: any, currentPath: string = 'playwright-suite') => {
    const nodeKey = `${currentPath}/${node.name}`;
    const isFolder = !!node.children;
    const isExpanded = expandedNodes[nodeKey] !== false;

    return (
      <div key={node.name} className="pl-4 select-none">
        <div 
          onClick={() => isFolder && toggleNode(nodeKey)}
          className={`flex items-center gap-1.5 py-1.5 rounded text-xs transition cursor-pointer font-mono ${
            isFolder ? 'text-[#7D8DA1] hover:text-text-primary' : 'text-text-primary hover:text-glow-bright'
          }`}
        >
          {isFolder ? (
            <>
              {isExpanded ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
              <Folder className="w-4 h-4 text-glow-blue fill-glow-blue/10 shrink-0" />
              <span className="font-semibold">{node.name}/</span>
            </>
          ) : (
            <>
              <div className="w-3.5 h-3.5" /> {/* spacer to align files */}
              <FileCode className="w-4 h-4 text-text-muted shrink-0" />
              <span>{node.name}</span>
            </>
          )}
        </div>

        {isFolder && isExpanded && (
          <div className="border-l border-border-custom/50 ml-6 pl-1">
            {node.children.map((child: any) => renderTree(child, nodeKey))}
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="p-6 h-full overflow-y-auto space-y-6 grid-bg bg-transparent relative z-10" id="eject-screen">
      
      {/* Page Header */}
      <div className="flex items-center gap-4">
        <CherenkovLogo variant="icon" size={42} />
        <div>
          <h1 className="font-display font-bold text-3xl text-text-primary tracking-tight">
            Export & Eject Suite
          </h1>
          <p className="text-sm text-[#7D8DA1] mt-1 leading-relaxed">
            Unlock your testing resources. Export 100% compliant Playwright code repositories without vendor lock-in.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6 items-start max-w-5xl">
        {/* Left Column: Confirmation form and success triggers (3/5 width) */}
        <div className="lg:col-span-3 space-y-6">
          <div className="bg-white/5 backdrop-blur-xl border border-white/10 p-6 rounded-2xl space-y-6 relative">
            <h2 className="text-lg font-display font-semibold text-text-primary flex items-center gap-2">
              <Download className="w-5 h-5 text-glow-bright" />
              <span>Eject Playwright Configuration</span>
            </h2>

            {!isEjected ? (
              // Stage 1: Configure run paths
              <div className="space-y-6 animate-fadeIn">
                
                {/* Reassurance Declaration Card block */}
                <div className="p-4 rounded-2xl bg-[#22d3ee]/10 border border-glow-blue/25 text-xs text-[#7D8DA1] space-y-2 leading-relaxed">
                  <div className="flex items-center gap-2 text-glow-bright font-semibold font-mono uppercase text-[10px]">
                    <Cpu className="w-4 h-4 text-glow-blue" />
                    <span>0% VENDOR LOCK-IN GUARANTEE</span>
                  </div>
                  <p>
                    Ejected test files do not include external calls or black-box API requirements. Ejecution complies strictly with global Playwright frameworks using plain <span className="font-mono text-glow-bright bg-black/35 px-1 py-0.5 rounded">npx playwright test</span>. Your tests belong to you.
                  </p>
                </div>

                {ejectError && (
                  <div className="p-4 rounded-2xl bg-danger-custom/10 border border-danger-custom/30 text-xs text-danger-custom space-y-2">
                    <div className="flex items-center gap-2 font-bold font-mono uppercase text-[10px]">
                      <AlertCircle className="w-4 h-4" />
                      <span>Eject Operation Failed</span>
                    </div>
                    <p className="font-mono">{ejectError}</p>
                  </div>
                )}

                {/* File summary telemetry check */}
                <div className="grid grid-cols-3 gap-2 bg-black/30 p-4 rounded-xl border border-white/5 text-xs text-center font-mono text-[#E6EDF3]">
                  <div>
                    <span className="block text-[9px] text-[#7D8DA1]/80 uppercase">Test Suites</span>
                    <span className="text-base font-bold font-sans text-glow-bright mt-1 block">47 Files</span>
                  </div>
                  <div>
                    <span className="block text-[9px] text-[#7D8DA1]/80 uppercase">API Clients</span>
                    <span className="text-base font-bold font-sans text-glow-bright mt-1 block">6 Classes</span>
                  </div>
                  <div>
                    <span className="block text-[9px] text-[#7D8DA1]/80 uppercase">Total Lines</span>
                    <span className="text-base font-bold font-sans text-glow-bright mt-1 block">~3.2 K</span>
                  </div>
                </div>

                {/* Path input field */}
                <div className="space-y-2">
                  <label htmlFor="eject-path" className="text-xs font-mono uppercase tracking-wider text-text-muted font-bold block">Output file destination path</label>
                  <div className="relative flex items-center">
                    <span className="absolute left-3.5 font-mono text-xs text-[#7D8DA1]">/home/workspace/</span>
                    <input
                      id="eject-path"
                      name="eject-path"
                      type="text"
                      value={outputPath}
                      onChange={(e) => setOutputPath(e.target.value)}
                      className="w-full bg-black/30 text-[#E6EDF3] text-xs font-mono pl-32 pr-4 py-3 rounded border border-white/10 focus:outline-none focus:border-glow-blue transition"
                    />
                  </div>
                  <span className="block text-[10px] text-text-muted font-mono leading-tight">
                    Creates any missing parent directories locally. Existing spec files will be safely archived (no overwriting override).
                  </span>
                </div>

                {/* Deploy Button */}
                <div className="flex gap-4">
                  <button
                    type="button"
                    id="btn-confirm-eject"
                    onClick={handleEject}
                    className="flex-1 h-11 bg-glow-blue hover:bg-opacity-95 text-slate-950 font-bold text-xs rounded-xl uppercase tracking-wider transition duration-300 shadow-lg shadow-cyan-500/20 flex items-center justify-center gap-2 cursor-pointer"
                  >
                    <HardDrive className="w-4 h-4 stroke-[2.5px]" />
                    <span>Eject to Path</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => { window.location.href = '/api/v1/eject/download'; }}
                    className="flex-1 h-11 bg-[#3FB950] hover:bg-opacity-95 text-[#FFFFFF] font-bold text-xs rounded-xl uppercase tracking-wider transition duration-300 shadow-lg shadow-green-500/20 flex items-center justify-center gap-2 cursor-pointer"
                  >
                    <Download className="w-4 h-4 stroke-[2.5px]" />
                    <span>Download .ZIP</span>
                  </button>
                </div>
              </div>
            ) : (
              // Stage 2: Successful copy instructions after eject
              <div className="space-y-6 animate-fadeIn select-none">
                <div className="p-4 bg-success-custom/10 border border-success-custom/25 rounded-2xl text-xs space-y-3">
                  <h4 className="font-bold text-[#3FB950] flex items-center gap-2 text-sm">
                    <CheckCircle className="w-5 h-5" />
                    <span>EXPORT FILE PROTOCOL WRITTEN SUCCESSFULLY</span>
                  </h4>
                  <p className="text-[#7D8DA1]/95 text-xs font-sans leading-relaxed">
                    Cherenkov written directory files successfully to <span className="font-mono text-glow-bright bg-black/40 px-1 py-0.5 rounded truncate">{outputPath}</span>. Follow these CLI operations inside your local workstation terminal to run tests:
                  </p>
                </div>

                {/* Copy Terminal Instruction */}
                <div className="space-y-2">
                  <span className="block text-[10px] font-mono text-[#7D8DA1] uppercase tracking-wider font-bold">Copy Instructions terminal</span>
                  
                  <div className="relative flex items-center bg-black/40 border border-white/10 rounded-xl overflow-hidden">
                    <pre className="flex-1 p-3.5 pr-24 font-mono text-[11px] text-[#E6EDF3] whitespace-pre-wrap select-all">
                      <code>{runCommandText}</code>
                    </pre>

                    <button
                      onClick={handleCopy}
                      id="btn-copy-command"
                      className="absolute right-2 px-3 py-1.5 rounded-xl bg-white/5 border border-white/10 hover:border-glow-blue text-[#E6EDF3] hover:text-glow-bright transition flex items-center gap-1 cursor-pointer"
                    >
                      {copySuccess ? (
                        <>
                          <CheckCircle className="w-3.5 h-3.5 text-[#3FB950]" />
                          <span className="text-[10px] font-mono uppercase font-bold text-[#3FB950]">COPIED</span>
                        </>
                      ) : (
                        <>
                          <Copy className="w-3.5 h-3.5" />
                          <span className="text-[10px] font-mono uppercase font-bold text-[#7D8DA1]">COPY</span>
                        </>
                      )}
                    </button>
                  </div>
                </div>

                {/* reset view */}
                <button
                  onClick={() => setIsEjected(false)}
                  className="text-xs font-mono text-glow-bright hover:underline cursor-pointer block"
                >
                  &larr; Return to eject configuration
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Right Column: Dynamic interactive file-tree model (2/5 width) */}
        <div className="lg:col-span-2 space-y-6">
          <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-2xl p-5 space-y-4">
            <h3 className="text-sm font-semibold text-[#E6EDF3] border-b border-white/5 pb-3 flex items-center gap-2">
              <HardDrive className="w-4 h-4 text-glow-blue" />
              <span>Project Folder Inspection Workspace</span>
            </h3>

            {/* Tree canvas background */}
            <div className="bg-black/30 border border-white/5 p-4 rounded-xl overflow-y-auto max-h-[360px] scrollbar-thin">
              {renderTree({name: 'playwright-suite', children: []})}
            </div>

            <p className="text-[10px] text-text-muted leading-relaxed font-sans text-center">
              📁 Click folders above to expand/inspect. Standard setup packages play perfectly inside generic Playwright docker instances.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
