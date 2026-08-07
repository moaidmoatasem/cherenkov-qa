/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Card } from '../../ui';
import { runPipeline, RunPipelineResponse } from '../../../lib/api';
import { Sparkles, Play, Terminal } from 'lucide-react';

interface IntentAuthoringPanelProps {
  specPath?: string;
  targetUrl?: string;
  onPipelineStarted?: (runId: string) => void;
}

export const IntentAuthoringPanel: React.FC<IntentAuthoringPanelProps> = ({
  specPath = '',
  targetUrl = 'http://localhost:8000',
  onPipelineStarted,
}) => {
  const [intent, setIntent] = useState('');
  const [currentSpecPath, setCurrentSpecPath] = useState(specPath);
  const [currentTargetUrl, setCurrentTargetUrl] = useState(targetUrl);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // J3: deep-link prefill. e.g. /authoring?intent=<pattern> from the
  // Knowledge Explorer "Author this check" CTA.
  const [searchParams] = useSearchParams();
  useEffect(() => {
    const fromIntent = searchParams.get('intent');
    if (fromIntent) {
      setIntent(fromIntent);
      setError(null);
    }
  }, [searchParams]);

  const handleRunIntent = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const res: RunPipelineResponse = await runPipeline({
        spec_path: currentSpecPath,
        target_url: currentTargetUrl,
        intent: intent.trim() || undefined,
      });
      if (onPipelineStarted && res.run_id) {
        onPipelineStarted(res.run_id);
      }
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card className="p-6 space-y-4" data-testid="intent-authoring-panel">
      <div>
        <h2 className="text-sm font-semibold font-mono uppercase tracking-wider text-text-muted flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-cyan-400" />
          <span>Intent-Driven Test Authoring</span>
        </h2>
        <p className="text-xs text-text-muted mt-0.5">
          Describe the API test behavior in natural language to generate verified Playwright suites.
        </p>
      </div>

      <form onSubmit={handleRunIntent} className="space-y-4">
        {/* Natural Language Prompt Area */}
        <div className="space-y-1.5">
          <label className="text-[10px] font-mono uppercase text-text-muted">Natural Language Test Intent</label>
          <textarea
            rows={3}
            value={intent}
            onChange={(e) => setIntent(e.target.value)}
            placeholder="e.g. Test user registration with invalid email format, verify 400 Bad Request, and validate JSON error schema..."
            className="w-full bg-bg-base text-text-primary text-xs p-3 rounded-xl border border-white/10 focus:outline-none focus:border-cyan-400 font-mono"
            data-testid="intent-input"
          />
        </div>

        {/* Spec Path & Target URL Inputs */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="space-y-1">
            <label className="text-[10px] font-mono uppercase text-text-muted">Spec Path / OpenAPI Reference</label>
            <input
              type="text"
              value={currentSpecPath}
              onChange={(e) => setCurrentSpecPath(e.target.value)}
              placeholder="cherenkov/stub/openapi.yaml"
              className="w-full bg-bg-base text-text-primary text-xs p-2 rounded-lg border border-white/10 font-mono"
            />
          </div>
          <div className="space-y-1">
            <label className="text-[10px] font-mono uppercase text-text-muted">Target Host URL</label>
            <input
              type="text"
              value={currentTargetUrl}
              onChange={(e) => setCurrentTargetUrl(e.target.value)}
              placeholder="http://localhost:8000"
              className="w-full bg-bg-base text-text-primary text-xs p-2 rounded-lg border border-white/10 font-mono"
            />
          </div>
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full py-2.5 bg-cyan-500/10 hover:bg-cyan-500/20 text-cyan-400 border border-cyan-500/30 rounded-xl text-xs font-mono font-bold flex items-center justify-center gap-2 transition cursor-pointer"
          data-testid="btn-generate-intent"
        >
          <Play className="w-4 h-4" />
          <span>{loading ? 'Triggering LLM Pipeline...' : 'Generate & Run Test Intent'}</span>
        </button>
      </form>

      {error && (
        <div className="p-3 bg-rose-500/10 border border-rose-500/30 rounded-xl text-xs text-rose-400 font-mono">
          Generation Error: {error}
        </div>
      )}
    </Card>
  );
};

export default IntentAuthoringPanel;
