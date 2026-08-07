/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React from 'react';
import ReleaseReadinessCard from './ReleaseReadinessCard';
import VerdictHistoryTable from './VerdictHistoryTable';
import IntegrityHeatmap from './IntegrityHeatmap';
import CoverageAndPerfScreen from './CoverageAndPerfScreen';
import CertificateVerification from './CertificateVerification';
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
        title="Dashboard"
        description="Is your API release-ready? Readiness score, run history, and coverage at a glance."
      />

      {/* 1. Release Readiness Gate KPI */}
      <ReleaseReadinessCard onNavigateToTriage={onNavigateToTriage} />

      {/* 2. Verdict History Table */}
      <VerdictHistoryTable onSelectRun={onSelectRun} />

      {/* 3. Spec Coverage & Risk Signals Heatmap */}
      <IntegrityHeatmap />

      {/* 4. Coverage Map, Trend & Performance Baselines */}
      <CoverageAndPerfScreen />

      {/* 5. Certificate Verification */}
      <CertificateVerification />
    </div>
  );
};

export default DashboardWorkspace;
