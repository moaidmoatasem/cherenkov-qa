/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState } from 'react';
import SpecIngestPanel from './SpecIngestPanel';
import DoctorCheckWidget from './DoctorCheckWidget';
import IntentAuthoringPanel from './IntentAuthoringPanel';
import LivePipelineMonitor from './LivePipelineMonitor';
import { PageHeader } from '../../ui/PageHeader';
import { EndpointRichness } from '../../../types';

export const AuthoringWorkspace: React.FC = () => {
  const [activeSpecPath, setActiveSpecPath] = useState<string>('');
  const [activeEndpoints, setActiveEndpoints] = useState<EndpointRichness[]>([]);
  const [activeRunId, setActiveRunId] = useState<string | undefined>(undefined);

  const handleSpecIngested = (path: string, endpoints: EndpointRichness[]) => {
    setActiveSpecPath(path);
    setActiveEndpoints(endpoints);
  };

  return (
    <div className="p-6 h-full overflow-y-auto space-y-6 grid-bg bg-transparent relative z-10" id="authoring-workspace">
      <PageHeader
        title="Authoring Workspace"
        description="OpenAPI spec ingestion, richness doctor checks, intent-driven test creation, and pipeline execution."
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
        onPipelineStarted={(runId) => setActiveRunId(runId)}
      />

      {/* 4. Live Pipeline DAG & Log Monitor */}
      <LivePipelineMonitor runId={activeRunId} />
    </div>
  );
};

export default AuthoringWorkspace;
