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
import { PageHeader } from '../../ui/PageHeader';
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

  const handleSpecIngested = (path: string, endpoints: EndpointRichness[]) => {
    setActiveSpecPath(path);
    setActiveEndpoints(endpoints);
  };

  const handlePipelineStarted = (runId: string) => {
    setActiveRunId(runId);
    onRunStarted?.(runId);
  };

  return (
    <div className="p-6 h-full overflow-y-auto space-y-6 grid-bg bg-transparent relative z-10" id="authoring-workspace">
      <PageHeader
        title="Generate Tests"
        description="Bring an OpenAPI spec, or describe a test in plain English, and get a generated test suite."
      />

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        {/* 1. Spec Ingestion Panel */}
        <SpecIngestPanel onSpecIngested={handleSpecIngested} />

        {/* 2. Doctor Check Widget */}
        <DoctorCheckWidget />
      </div>

      {/* 3. Intent-Driven Test Authoring */}
      <IntentAuthoringPanel
        specPath={activeSpecPath}
        onPipelineStarted={handlePipelineStarted}
      />

      {/* 4. Live Surface Explorer — crawl a running service for anomalies */}
      <ExplorePanel />

      {/* 5. Detected multi-step CRUD chains for the ingested spec */}
      <DetectedChainsPanel specPath={activeSpecPath} />

      {/* 6. Live Pipeline DAG & Log Monitor */}
      <LivePipelineMonitor runId={activeRunId} />
    </div>
  );
};

export default AuthoringWorkspace;
