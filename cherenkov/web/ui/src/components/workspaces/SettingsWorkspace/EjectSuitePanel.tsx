/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState } from 'react';
import { Card } from '../../ui';
import { ejectSuite, EjectResponse } from '../../../lib/api';
import { Download, CheckCircle2, HardDrive, Cpu, AlertCircle, Copy, Check } from 'lucide-react';

export const EjectSuitePanel: React.FC = () => {
  const [outputPath, setOutputPath] = useState('./playwright-suite');
  const [isEjected, setIsEjected] = useState(false);
  const [ejectResponse, setEjectResponse] = useState<EjectResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const runCommandText = `cd playwright-suite && npm install && npx playwright test`;

  const handleEject = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await ejectSuite(outputPath);
      setEjectResponse(res);
      setIsEjected(true);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleCopy = () => {
    navigator.clipboard.writeText(runCommandText);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <Card className="p-6 space-y-4 font-mono text-xs" data-testid="eject-suite-panel">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold uppercase tracking-wider text-text-muted flex items-center gap-2">
            <Download className="w-4 h-4 text-cyan-400" />
            <span>Plain Playwright Suite Exporter (Zero Lock-in)</span>
          </h2>
          <p className="text-xs text-text-muted mt-0.5 font-sans">
            Export 100% compliant Playwright code repositories without vendor lock-in via <code className="font-mono">/api/v1/eject</code>.
          </p>
        </div>
      </div>

      {!isEjected ? (
        <div className="space-y-4">
          <div className="p-3 bg-cyan-500/10 border border-cyan-500/30 rounded-xl text-text-primary text-xs space-y-1">
            <p className="font-bold text-cyan-400 uppercase text-[10px] flex items-center gap-1">
              <Cpu className="w-3.5 h-3.5" /> Anti-Lock-in Guarantee (D7)
            </p>
            <p className="text-[11px] leading-relaxed font-sans">
              Ejected suites run via plain <code className="font-mono text-cyan-400">npx playwright test</code> with zero external CHERENKOV dependencies.
            </p>
          </div>

          <div className="space-y-1.5">
            <label className="text-[10px] uppercase text-text-muted">Destination Output Path</label>
            <input
              type="text"
              value={outputPath}
              onChange={(e) => setOutputPath(e.target.value)}
              aria-label="Eject output path"
              className="w-full bg-bg-base text-text-primary p-2.5 rounded-lg border border-white/10"
              data-testid="eject-output-path"
            />
          </div>

          <button
            onClick={handleEject}
            disabled={isLoading}
            className="w-full py-2.5 bg-cyan-500/20 hover:bg-cyan-500/30 text-cyan-400 border border-cyan-500/40 rounded-xl font-bold flex items-center justify-center gap-2 transition cursor-pointer"
            data-testid="btn-run-eject"
          >
            <HardDrive className="w-4 h-4" />
            <span>{isLoading ? 'Exporting Playwright Suite...' : 'Eject Suite Now'}</span>
          </button>

          {error && <div className="p-3 bg-rose-500/10 border border-rose-500/30 text-rose-400 rounded-xl text-xs">{error}</div>}
        </div>
      ) : (
        <div className="space-y-4">
          <div className="p-3 bg-emerald-500/10 border border-emerald-500/30 rounded-xl text-emerald-400 text-xs flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 shrink-0" />
            <span>Eject successful! Suite written to {ejectResponse?.output_path || outputPath}.</span>
          </div>

          <div className="p-3 bg-black/40 border border-white/10 rounded-xl space-y-2">
            <div className="flex items-center justify-between text-[10px] text-text-muted">
              <span>RUN INSTRUCTIONS</span>
              <button onClick={handleCopy} className="text-cyan-400 flex items-center gap-1">
                {copied ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                {copied ? 'Copied' : 'Copy'}
              </button>
            </div>
            <pre className="text-emerald-400 text-xs">{runCommandText}</pre>
          </div>

          <button
            onClick={() => setIsEjected(false)}
            className="text-xs text-cyan-400 hover:underline"
          >
            &larr; Configure Export Settings
          </button>
        </div>
      )}
    </Card>
  );
};

export default EjectSuitePanel;
