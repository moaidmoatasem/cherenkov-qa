/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState } from 'react';
import HitlReviewQueue from './HitlReviewQueue';
import DivergenceTable from './DivergenceTable';
import SpecVsRealityDiffViewer from './SpecVsRealityDiffViewer';
import HealingSuggestionsPanel from './HealingSuggestionsPanel';
import { PageHeader } from '../../ui/PageHeader';
import { Divergence } from '../../../types';

export const TriageWorkspace: React.FC = () => {
  const [selectedDivergence, setSelectedDivergence] = useState<Divergence | undefined>(undefined);

  return (
    <div className="p-6 h-full overflow-y-auto space-y-6 grid-bg bg-transparent relative z-10" id="triage-workspace">
      <PageHeader
        title="Triage"
        description="Review what the AI flagged, compare spec vs. real API behavior, and approve or reject before anything lands in your suite."
      />

      {/* 1. HITL Test Approval Review Queue */}
      <HitlReviewQueue />

      {/* 2. Divergence Triage Table */}
      <DivergenceTable onSelectDivergence={(div) => setSelectedDivergence(div)} />

      {/* 3. Spec vs Reality Payload Diff Viewer */}
      <SpecVsRealityDiffViewer divergenceId={selectedDivergence?.id} />

      {/* 4. Suggest-Only Healing */}
      <HealingSuggestionsPanel />
    </div>
  );
};

export default TriageWorkspace;
