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
import { Play, Zap, Radar, CornerDownRight } from 'lucide-react';

interface DashboardWorkspaceProps {
  onNavigateToTriage?: () => void;
  onSelectRun?: (run: RunRecord) => void;
  /** N-2: section landing links. */
  onNavigate?: (workspace: 'authoring' | 'triage') => void;
  activeRunId?: string | null;
}

export const DashboardWorkspace: React.FC<DashboardWorkspaceProps> = ({
  onNavigateToTriage,
  onSelectRun,
  onNavigate,
  activeRunId,
}) => {
  const quickLinks = [
    {
      id: 'resume-run',
      label: 'Resume active run',
      detail: activeRunId ? `Continue run ${activeRunId.slice(0, 8)}…` : 'No active run in this session',
      icon: Play,
      to: 'authoring' as const,
      disabled: !activeRunId,
    },
    {
      id: 'review-divergences',
      label: 'Open recent divergence',
      detail: 'Jump to the risk-scored triage table',
      icon: Zap,
      to: 'triage' as const,
      disabled: false,
    },
    {
      id: 'explore-surface',
      label: 'Explore a live surface',
      detail: 'Crawl a running service for anomalies',
      icon: Radar,
      to: 'authoring' as const,
      disabled: false,
    },
  ];

  return (
    <div className="p-6 h-full overflow-y-auto space-y-6 grid-bg bg-transparent relative z-10" id="dashboard-workspace">
      <PageHeader
        title="Dashboard"
        description="Is your API release-ready? Readiness score, run history, and coverage at a glance."
      />

      {/* 0. Section Landing Links (N-2) */}
      <div className="flex flex-wrap gap-3" data-testid="dashboard-quick-links">
        {quickLinks.map((link) => {
          const Icon = link.icon;
          return (
            <button
              key={link.id}
              onClick={() => onNavigate && onNavigate(link.to)}
              disabled={link.disabled}
              data-testid={`quick-link-${link.id}`}
              className={`flex items-center gap-3 px-4 py-2.5 rounded-xl border text-left transition ${
                link.disabled
                  ? 'border-border-subtle bg-bg-surface/40 text-text-muted/50 cursor-not-allowed'
                  : 'border-border-subtle bg-bg-surface/70 hover:border-cyan-500/40 hover:bg-cyan-500/5 text-text-primary cursor-pointer'
              }`}
            >
              <Icon className={`w-4 h-4 shrink-0 ${link.disabled ? 'text-text-muted/50' : 'text-cyan-400'}`} />
              <span className="min-w-0">
                <span className="block text-xs font-mono font-semibold">{link.label}</span>
                <span className="block text-[10px] text-text-muted truncate max-w-[16rem]">{link.detail}</span>
              </span>
              <CornerDownRight className="w-3 h-3 text-text-muted/50 shrink-0" />
            </button>
          );
        })}
      </div>

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
