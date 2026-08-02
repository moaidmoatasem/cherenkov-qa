/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useCallback, useMemo } from 'react';
import { BrowserRouter, useNavigate, useLocation } from 'react-router-dom';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import LoginPage from './components/LoginPage';
import AppHeader from './components/layout/AppHeader';
import NavigationBar, { WorkspaceId } from './components/layout/NavigationBar';
import DashboardWorkspace from './components/workspaces/DashboardWorkspace';
import AuthoringWorkspace from './components/workspaces/AuthoringWorkspace';
import TriageWorkspace from './components/workspaces/TriageWorkspace';
import IntelligenceWorkspace from './components/workspaces/IntelligenceWorkspace';
import SettingsWorkspace from './components/workspaces/SettingsWorkspace';
import CommandPalette from './components/CommandPalette';
import GlobalShortcuts from './components/GlobalShortcuts';
import { ErrorBoundary } from './components/ErrorBoundary';
import GuidedTour from './components/GuidedTour';
import { OfflineOverlay } from './components/ui';
import { useToast } from './components/ui/Toast';
import OnboardingWizard from './components/OnboardingWizard';
import { Project } from './types';
import { fetchProjects, fetchMetricsData, fetchReviewQueue, runPipeline } from './lib/api';
import { useHealth } from './lib/useHealth';
import { listenDesktop } from './lib/tauri';

function InnerApp() {
  const { authRequired, loading: authLoading, user, logout } = useAuth();
  const { toast } = useToast();
  const navigate = useNavigate();
  const location = useLocation();

  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null);

  React.useEffect(() => {
    fetchProjects().then((data) => {
      setProjects(data || []);
      if (data && data.length > 0 && !selectedProjectId) {
        setSelectedProjectId(data[0].id);
      }
    });
  }, []);

  // Map route path to WorkspaceId
  const activeWorkspace: WorkspaceId = useMemo(() => {
    const p = location.pathname.replace(/^[/]+/, '');
    if (!p || p === 'index.html' || p === 'dashboard' || ['overview', 'verdict', 'truth-map', 'signals', 'coverage'].includes(p)) {
      return 'dashboard';
    }
    if (p === 'authoring' || ['author', 'setup', 'pipeline', 'explore'].includes(p)) {
      return 'authoring';
    }
    if (p === 'triage' || ['review', 'divergences', 'healing', 'spec-vs-reality'].includes(p)) {
      return 'triage';
    }
    if (p === 'intelligence' || ['chat', 'knowledge', 'sdd', 'memory'].includes(p)) {
      return 'intelligence';
    }
    if (p === 'settings' || ['projects', 'devices', 'mobile', 'eject', 'governance', 'ui-kit'].includes(p)) {
      return 'settings';
    }
    return 'dashboard';
  }, [location.pathname]);

  const handleSelectWorkspace = useCallback(
    (ws: WorkspaceId) => {
      navigate(`/${ws}`);
    },
    [navigate]
  );

  const workspaceTitles: Record<WorkspaceId, { title: string; subtitle: string }> = {
    dashboard: { title: 'Dashboard Workspace', subtitle: 'Release Readiness Overview & Verdict History' },
    authoring: { title: 'Authoring Workspace', subtitle: 'OpenAPI Spec Ingestion & Natural Language Intent Studio' },
    triage: { title: 'Triage Workspace', subtitle: 'HITL Test Review Queue & Divergence Resolution' },
    intelligence: { title: 'Intelligence Workspace', subtitle: 'GraphRAG Second Brain & SDD Memory Budget Cockpit' },
    settings: { title: 'Settings Workspace', subtitle: 'Hardware, VLM Devices & System Governance' },
  };

  // Backend liveness — single source of truth for offline state
  const { online, checking, refresh, lastCheckedAt } = useHealth();

  React.useEffect(() => {
    const subs = ['engine-healthy', 'engine-demo-mode', 'engine-stopped'].map((evt) =>
      listenDesktop(evt, () => refresh())
    );
    return () => {
      subs.forEach((p) => p.then((unlisten) => unlisten()));
    };
  }, [refresh]);

  // Observability Token pool metrics
  const [tokenUsagePercent, setTokenUsagePercent] = useState(0);
  const [totalSpentEstimated, setTotalSpentEstimated] = useState(0);

  React.useEffect(() => {
    const poll = () => {
      fetchMetricsData()
        .then((data) => {
          const { totalTokens, totalCost } = data.metrics;
          setTokenUsagePercent(Math.min(100, Math.round((totalTokens / 50000) * 100)));
          setTotalSpentEstimated(totalCost);
        })
        .catch(() => {});
    };
    poll();
    const id = setInterval(poll, 30_000);
    return () => clearInterval(id);
  }, []);

  // Live review queue badge count
  const [reviewPendingCount, setReviewPendingCount] = useState(0);
  React.useEffect(() => {
    const pollQueue = () => {
      fetchReviewQueue('pending')
        .then((items) => setReviewPendingCount(Array.isArray(items) ? items.length : 0))
        .catch(() => {});
    };
    pollQueue();
    const id = setInterval(pollQueue, 30_000);
    return () => clearInterval(id);
  }, []);

  // Guided Tour state
  const [showTour, setShowTour] = useState(() => {
    const path = window.location.pathname;
    const isDeepLink = path !== '/' && path !== '/index.html' && path !== '/setup' && path !== '/projects';
    if (isDeepLink) {
      localStorage.setItem('[copilot] tour_seen', 'true');
      return false;
    }
    return localStorage.getItem('[copilot] tour_seen') !== 'true';
  });

  const handleCloseTour = () => {
    setShowTour(false);
    localStorage.setItem('[copilot] tour_seen', 'true');
  };

  // Onboarding Wizard state
  const [showOnboarding, setShowOnboarding] = useState(() => {
    return localStorage.getItem('[cherenkov] onboarding_seen') !== 'true';
  });

  const handleCompleteOnboarding = () => {
    setShowOnboarding(false);
    localStorage.setItem('[cherenkov] onboarding_seen', 'true');
  };

  const handleEnableDemo = async () => {
    try {
      await runPipeline({ spec_path: '', demo_mode: true });
    } catch (e) {
      toast(`Demo enable failed: ${(e as Error).message}`, 'danger');
    }
  };

  // Auth gate
  if (authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-bg-base text-text-secondary text-sm font-mono">
        Initializing Cherenkov Engine...
      </div>
    );
  }
  if (authRequired && !user) {
    return <LoginPage />;
  }

  return (
    <>
      <GlobalShortcuts onNewRun={() => handleSelectWorkspace('authoring')} onSearch={() => {}} />
      <ErrorBoundary>
        <div className="flex h-screen w-screen overflow-hidden bg-bg-base text-text-primary font-sans antialiased flex-col relative" id="cherenkov-app-core">
          {/* Background Gradient Orbs */}
          <div className="absolute top-[-200px] left-[-200px] w-[600px] h-[600px] bg-cyan-500/10 rounded-full blur-[120px] pointer-events-none z-0" />
          <div className="absolute bottom-[-100px] right-[-100px] w-[500px] h-[500px] bg-blue-600/10 rounded-full blur-[100px] pointer-events-none z-0" />

          {/* Command Palette */}
          <CommandPalette
            onNavigate={(tab) => {
              if (tab === 'projects' || tab === 'settings' || tab === 'devices' || tab === 'eject' || tab === 'governance') {
                handleSelectWorkspace('settings');
              } else if (tab === 'setup' || tab === 'pipeline' || tab === 'author' || tab === 'explore') {
                handleSelectWorkspace('authoring');
              } else if (tab === 'review' || tab === 'divergences' || tab === 'healing' || tab === 'spec-vs-reality') {
                handleSelectWorkspace('triage');
              } else if (tab === 'chat' || tab === 'knowledge' || tab === 'sdd' || tab === 'memory') {
                handleSelectWorkspace('intelligence');
              } else {
                handleSelectWorkspace('dashboard');
              }
            }}
            onNewRun={() => handleSelectWorkspace('authoring')}
            projects={projects}
            onSelectProject={(id) => setSelectedProjectId(id)}
          />

          {showOnboarding && (
            <OnboardingWizard onComplete={handleCompleteOnboarding} onEnableDemo={handleEnableDemo} />
          )}

          {showTour && !showOnboarding && (
            <GuidedTour onClose={handleCloseTour} onNavigate={(tab) => handleSelectWorkspace('dashboard')} />
          )}

          {!online && <OfflineOverlay checking={checking} onRetry={refresh} lastCheckedAt={lastCheckedAt} />}

          {/* 1. App Header */}
          <AppHeader
            activeWorkspaceTitle={workspaceTitles[activeWorkspace].title}
            activeWorkspaceSubtitle={workspaceTitles[activeWorkspace].subtitle}
            selectedProjectId={selectedProjectId}
            onSelectProject={(id) => setSelectedProjectId(id)}
            tokenUsagePercent={tokenUsagePercent}
            totalSpentEstimated={totalSpentEstimated}
            online={online}
          />

          {/* 2. Main Layout Body with NavigationBar & 5 Workspaces */}
          <div className="flex-1 flex overflow-hidden">
            <NavigationBar
              activeWorkspace={activeWorkspace}
              onSelectWorkspace={handleSelectWorkspace}
              pendingReviewCount={reviewPendingCount}
              onNewRun={() => handleSelectWorkspace('authoring')}
            />

            <main className="flex-1 overflow-hidden h-full">
              {activeWorkspace === 'dashboard' && (
                <DashboardWorkspace onNavigateToTriage={() => handleSelectWorkspace('triage')} />
              )}
              {activeWorkspace === 'authoring' && <AuthoringWorkspace />}
              {activeWorkspace === 'triage' && <TriageWorkspace />}
              {activeWorkspace === 'intelligence' && <IntelligenceWorkspace />}
              {activeWorkspace === 'settings' && <SettingsWorkspace />}
            </main>
          </div>
        </div>
      </ErrorBoundary>
    </>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <InnerApp />
      </AuthProvider>
    </BrowserRouter>
  );
}
