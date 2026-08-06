/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useCallback, useMemo } from 'react';
import {
  BrowserRouter,
  Navigate,
  Route,
  Routes,
  useNavigate,
  useLocation,
} from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import LoginPage from './components/LoginPage';
import AppHeader from './components/layout/AppHeader';
import NavigationBar, { WorkspaceId } from './components/layout/NavigationBar';
import JourneyStepper from './components/layout/JourneyStepper';
import DashboardWorkspace from './components/workspaces/DashboardWorkspace';
import AuthoringWorkspace from './components/workspaces/AuthoringWorkspace';
import TriageWorkspace from './components/workspaces/TriageWorkspace';
import IntelligenceWorkspace from './components/workspaces/IntelligenceWorkspace';
import SettingsWorkspace from './components/workspaces/SettingsWorkspace';
import MobilePilotScreen from './components/MobilePilotScreen';
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
import {
  JourneyProvider,
  SURFACE_CHROME,
  SURFACE_TITLES,
  surfaceFromPath,
} from './journey/config';

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

  const activeWorkspace: WorkspaceId = useMemo(
    () => surfaceFromPath(location.pathname),
    [location.pathname]
  );

  const handleSelectWorkspace = useCallback(
    (ws: WorkspaceId) => {
      navigate(`/${ws}`);
    },
    [navigate]
  );

  // The run the journey stepper reflects. Held here rather than inside
  // AuthoringWorkspace so it survives navigating away from the page that
  // started it -- the whole point of a rail that is always visible. Seeded
  // from ?run= so a run stays visible across a reload and can be linked to.
  const [activeRunId, setActiveRunId] = useState<string | null>(
    () => new URLSearchParams(window.location.search).get('run')
  );

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
            // The palette emits surface ids now; surfaceFromPath still accepts
            // the legacy names so an old bookmark or muscle memory resolves.
            onNavigate={(tab) => handleSelectWorkspace(surfaceFromPath(tab))}
            onNewRun={() => handleSelectWorkspace('authoring')}
            projects={projects}
            onSelectProject={(id) => setSelectedProjectId(id)}
          />

          {showOnboarding && (
            <OnboardingWizard onComplete={handleCompleteOnboarding} onEnableDemo={handleEnableDemo} />
          )}

          {showTour && !showOnboarding && (
            <GuidedTour onClose={handleCloseTour} onNavigate={handleSelectWorkspace} />
          )}

          {!online && <OfflineOverlay checking={checking} onRetry={refresh} lastCheckedAt={lastCheckedAt} />}

          {/* 1. App Header */}
          <AppHeader
            activeWorkspaceTitle={SURFACE_TITLES[activeWorkspace].title}
            activeWorkspaceSubtitle={SURFACE_TITLES[activeWorkspace].subtitle}
            selectedProjectId={selectedProjectId}
            onSelectProject={(id) => setSelectedProjectId(id)}
            tokenUsagePercent={tokenUsagePercent}
            totalSpentEstimated={totalSpentEstimated}
            online={online}
          />

          {/* 2. Journey Stepper -- always-visible "where am I in the loop" rail.
              Its progress comes from the active run, not from the current page. */}
          <JourneyStepper
            activeWorkspace={activeWorkspace}
            onSelectWorkspace={handleSelectWorkspace}
            pendingReviewCount={reviewPendingCount}
            activeRunId={activeRunId}
          />

          {/* 3. Main Layout Body with NavigationBar & 5 Workspaces */}
          <div className="flex-1 flex overflow-hidden">
            <NavigationBar
              activeWorkspace={activeWorkspace}
              onSelectWorkspace={handleSelectWorkspace}
              pendingReviewCount={reviewPendingCount}
              onNewRun={() => handleSelectWorkspace('authoring')}
            />

            <main className="flex-1 overflow-hidden h-full">
              <Routes>
                <Route
                  path="/dashboard"
                  element={
                    <DashboardWorkspace
                      onNavigateToTriage={() => handleSelectWorkspace('triage')}
                    />
                  }
                />
                <Route
                  path="/authoring"
                  element={<AuthoringWorkspace onRunStarted={setActiveRunId} />}
                />
                <Route path="/triage" element={<TriageWorkspace />} />
                <Route path="/intelligence" element={<IntelligenceWorkspace />} />
                <Route path="/settings" element={<SettingsWorkspace />} />
                <Route path="/mobile" element={<MobilePilotScreen />} />
                {/* Legacy deep links keep working instead of 404ing. */}
                {(Object.keys(SURFACE_CHROME) as WorkspaceId[]).flatMap((surface) =>
                  SURFACE_CHROME[surface].aliases.map((alias) => (
                    <Route
                      key={alias}
                      path={`/${alias}`}
                      element={<Navigate to={`/${surface}`} replace />}
                    />
                  ))
                )}
                <Route path="*" element={<Navigate to="/dashboard" replace />} />
              </Routes>
            </main>
          </div>
        </div>
      </ErrorBoundary>
    </>
  );
}

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      // A session that has expired should send the user to the login page, not
      // be retried three times per panel.
      retry: (failureCount, error) =>
        !/Session expired/.test((error as Error).message) && failureCount < 2,
      refetchOnWindowFocus: false,
    },
  },
});

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AuthProvider>
          <JourneyProvider>
            <InnerApp />
          </JourneyProvider>
        </AuthProvider>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
