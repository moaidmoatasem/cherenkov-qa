/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React from 'react';
import ReleaseReadinessCard from './ReleaseReadinessCard';
import VerdictHistoryTable from './VerdictHistoryTable';
import IntegrityHeatmap from './IntegrityHeatmap';
import CertificateVerificationPanel from './CertificateVerificationPanel';
import { PageHeader } from '../../ui/PageHeader';
import { RunRecord } from '../../../lib/api';

interface DashboardWorkspaceProps {
  onNavigateToTriage?: () => void;
  onSelectRun?: (run: RunRecord) => void;
}

export const DashboardWorkspace: React.FC<DashboardWorkspaceProps> = ({
  onNavigateToTriage,
  onSelectRun,
}) => {
  return (
    <div className="p-6 h-full overflow-y-auto space-y-6 grid-bg bg-transparent relative z-10" id="dashboard-workspace">
      <PageHeader
        title="Dashboard Workspace"
        description="Release readiness overview, verdict history, spec coverage integrity, and certificate verification."
      />

      {/* 1. Release Readiness Gate KPI */}
      <ReleaseReadinessCard onNavigateToTriage={onNavigateToTriage} />

      {/* 2. Verdict History Table */}
      <VerdictHistoryTable onSelectRun={onSelectRun} />

      {/* 3. Spec Coverage & Risk Signals Heatmap */}
      <IntegrityHeatmap />

      {/* 4. Certificate Verification */}
      <CertificateVerificationPanel />
    </div>
  );
};

export default DashboardWorkspace;
