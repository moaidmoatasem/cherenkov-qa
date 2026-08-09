/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState } from 'react';
import ReleaseReadinessCard from './ReleaseReadinessCard';
import VerdictHistoryTable from './VerdictHistoryTable';
import IntegrityHeatmap from './IntegrityHeatmap';
import CoverageAndPerfScreen from './CoverageAndPerfScreen';
import CertificateVerification from './CertificateVerification';
import TestSurfacesPanel from './TestSurfacesPanel';
import { PageHeader } from '../../ui/PageHeader';
import { Tabs } from '../../ui/Tabs';
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
  const [activeTab, setActiveTab] = useState('overview');

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
    <div className="ds-flex-col ds-gap-lg" style={{ padding: 'var(--spacing-xl)', height: '100%', overflowY: 'auto', background: 'transparent', position: 'relative', zIndex: 10 }} id="dashboard-workspace">
      <PageHeader
        title="Dashboard"
        description="Is your API release-ready? Readiness score, run history, and coverage at a glance."
        tabs={
          <Tabs
            items={[
              { id: 'overview', label: 'Overview' },
              { id: 'signals', label: 'Coverage & Signals' }
            ]}
            activeId={activeTab}
            onChange={setActiveTab}
          />
        }
      />

      {activeTab === 'overview' && (
        <div className="ds-flex-col ds-gap-lg" style={{ animation: 'ds-pulse 0.3s ease-out forwards' }}>
          {/* 0. Section Landing Links (N-2) */}
          <div className="ds-flex-row ds-gap-md" style={{ flexWrap: 'wrap' }} data-testid="dashboard-quick-links">
            {quickLinks.map((link) => {
              const Icon = link.icon;
              return (
                <button
                  key={link.id}
                  onClick={() => onNavigate && onNavigate(link.to)}
                  disabled={link.disabled}
                  data-testid={`quick-link-${link.id}`}
                  className={`ds-button ds-glass-panel ds-flex-row ds-gap-sm ${link.disabled ? 'ds-disabled' : 'ds-button-primary'}`}
                  style={{ opacity: link.disabled ? 0.5 : 1, textAlign: 'left', padding: '12px 16px' }}
                >
                  <Icon style={{ width: '16px', height: '16px', flexShrink: 0, color: link.disabled ? 'var(--text-muted)' : 'var(--primary)' }} />
                  <span style={{ minWidth: 0, display: 'flex', flexDirection: 'column' }}>
                    <span className="ds-title" style={{ fontSize: '13px' }}>{link.label}</span>
                    <span className="ds-subtitle" style={{ maxWidth: '256px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{link.detail}</span>
                  </span>
                  <CornerDownRight style={{ width: '12px', height: '12px', color: 'var(--text-muted)', flexShrink: 0 }} />
                </button>
              );
            })}
          </div>

          {/* 1. Release Readiness Gate KPI */}
          <ReleaseReadinessCard onNavigateToTriage={onNavigateToTriage} />

          {/* 2. Verdict History Table */}
          <VerdictHistoryTable onSelectRun={onSelectRun} />

          {/* 5. Certificate Verification */}
          <CertificateVerification />
        </div>
      )}

      {activeTab === 'signals' && (
        <div className="ds-flex-col ds-gap-lg" style={{ animation: 'ds-pulse 0.3s ease-out forwards' }}>
          {/* 3. Spec Coverage & Risk Signals Heatmap */}
          <IntegrityHeatmap />

          {/* 4. Coverage Map, Trend & Performance Baselines */}
          <CoverageAndPerfScreen />

          {/* 5. Web UI Probe + k6 Performance — secondary surfaces (#882) */}
          <TestSurfacesPanel />
        </div>
      )}
    </div>
  );
};

export default DashboardWorkspace;
