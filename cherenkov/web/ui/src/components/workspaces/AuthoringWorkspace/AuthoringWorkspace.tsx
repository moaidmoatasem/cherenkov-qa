/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState } from 'react';
import SpecIngestPanel from './SpecIngestPanel';
import DoctorCheckWidget from './DoctorCheckWidget';
import IntentAuthoringPanel from './IntentAuthoringPanel';
import LivePipelineMonitor from './LivePipelineMonitor';
import DetectedChainsPanel from './DetectedChainsPanel';
import ExplorePanel from './ExplorePanel';
import VisionFallbackBanner from './VisionFallbackBanner';
import { PageHeader } from '../../ui/PageHeader';
import { runPipeline } from '../../../lib/api';
import { EndpointRichness } from '../../../types';

export interface AuthoringWorkspaceProps {
  /** Lifts the run id to the shell so the journey stepper keeps tracking it
   *  after the user navigates away from this page. */
  onRunStarted?: (runId: string) => void;
}

export const AuthoringWorkspace: React.FC<AuthoringWorkspaceProps> = ({
  onRunStarted,
}) => {
  const [activeSpecPath, setActiveSpecPath] = useState<string>('');
  const [activeEndpoints, setActiveEndpoints] = useState<EndpointRichness[]>([]);
  const [activeRunId, setActiveRunId] = useState<string | undefined>(undefined);
  const [generating, setGenerating] = useState(false);
  const [generateError, setGenerateError] = useState<string | null>(null);

  const handleSpecIngested = (path: string, endpoints: EndpointRichness[]) => {
    setActiveSpecPath(path);
    setActiveEndpoints(endpoints);
    setGenerateError(null);
  };

  const handlePipelineStarted = (runId: string) => {
    setActiveRunId(runId);
    onRunStarted?.(runId);
  };

  /** Generate a suite for the whole ingested spec — no intent needed. */
  const handleGenerate = async () => {
    if (!activeSpecPath) return;
    setGenerating(true);
    setGenerateError(null);
    try {
      const res = await runPipeline({ spec_path: activeSpecPath });
      if (res.run_id) handlePipelineStarted(res.run_id);
      // The run's progress renders further down the page; move the user there
      // rather than leaving them looking at an unchanged panel.
      document
        .getElementById('live-pipeline-monitor')
        ?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    } catch (err) {
      setGenerateError((err as Error).message);
    } finally {
      setGenerating(false);
    }
  };

  return (
    <div className="p-6 h-full overflow-y-auto space-y-6 grid-bg bg-transparent relative z-10" id="authoring-workspace">
      <PageHeader
        title="Generate Tests"
        description="Bring an OpenAPI spec, or describe a test in plain English, and get a generated test suite."
      />

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        {/* 1. Spec Ingestion Panel */}
        <SpecIngestPanel
          onSpecIngested={handleSpecIngested}
          onGenerate={handleGenerate}
          generating={generating}
        />

        {/* 2. Doctor Check Widget */}
        <DoctorCheckWidget />
      </div>

      {generateError && (
        <div
          role="alert"
          className="p-3 bg-rose-500/10 border border-rose-500/30 rounded-xl text-xs font-mono text-rose-400"
        >
          Could not start generation: {generateError}
        </div>
      )}

      {/* 3. Intent-Driven Test Authoring */}
      <IntentAuthoringPanel
        specPath={activeSpecPath}
        onPipelineStarted={handlePipelineStarted}
      />

      {/* 3b. Vision fallback availability (J1) */}
      <VisionFallbackBanner />

      {/* 4. Live Surface Explorer — crawl a running service for anomalies */}
      <ExplorePanel />

      {/* 5. Detected multi-step CRUD chains for the ingested spec */}
      <DetectedChainsPanel specPath={activeSpecPath} />

      {/* 6. Live Pipeline DAG & Log Monitor */}
      <div id="live-pipeline-monitor">
        <LivePipelineMonitor runId={activeRunId} />
      </div>
    </div>
  );
};

export default AuthoringWorkspace;
