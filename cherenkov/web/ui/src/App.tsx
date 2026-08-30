/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useCallback, useMemo, Suspense, lazy } from 'react';
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
import NavigationBar from './components/layout/NavigationBar';
import JourneyStepper from './components/layout/JourneyStepper';
import MobilePilotScreen from './components/MobilePilotScreen';
import CommandPalette from './components/CommandPalette';
import GlobalShortcuts from './components/GlobalShortcuts';
import { ErrorBoundary } from './components/ErrorBoundary';
import GuidedTour from './components/GuidedTour';
import KeyboardMapOverlay from './components/KeyboardMapOverlay';
import { OfflineOverlay } from './components/ui';
import { Breadcrumbs } from './components/ui/Breadcrumbs';
import { useToast } from './components/ui/Toast';
import OnboardingWizard from './components/OnboardingWizard';
import { Project } from './types';
import { fetchProjects, fetchMetricsData, fetchReviewQueue, runPipeline } from './lib/api';
import { useHealth } from './lib/useHealth';
import { useDensity } from './lib/useDensity';
import { listenDesktop } from './lib/tauri';
import {
  JourneyProvider,
  SURFACE_CHROME,
  SURFACE_TITLES,
  surfaceFromPath,
} from './journey/config';
import type { WorkspaceId } from './journey/types';

// Workspaces are the app's heavy chunks (tables, charts, chat). Split each on
// its own boundary so the first paint loads only the shell + one workspace.
const DashboardWorkspace = lazy(() => import('./components/workspaces/DashboardWorkspace'));
const AuthoringWorkspace = lazy(() => import('./components/workspaces/AuthoringWorkspace'));
const TriageWorkspace = lazy(() => import('./components/workspaces/TriageWorkspace'));
const IntelligenceWorkspace = lazy(() => import('./components/workspaces/IntelligenceWorkspace'));
const SettingsWorkspace = lazy(() => import('./components/workspaces/SettingsWorkspace'));
const EnterpriseWorkspace = lazy(() => import('./components/workspaces/EnterpriseWorkspace/EnterpriseWorkspace'));

const WorkspaceFallback = () => (
  <div className="h-full flex items-center justify-center bg-bg-base text-text-muted text-sm font-mono animate-pulse" role="status">
    Loading workspace...
  </div>
);

function InnerApp() {
  const { authRequired, loading: authLoading, user, logout } = useAuth();
  const { toast } = useToast();
  const navigate = useNavigate();
  const location = useLocation();

  // Applies the persisted Comfortable/Compact density to <html> on load.
  useDensity();

  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null);
  // Mobile nav drawer. Desktop ignores this entirely -- the sidebar is static
  // from lg up.
  const [navDrawerOpen, setNavDrawerOpen] = useState(false);

  // N-4: last-visited surfaces for the command palette "RECENT" section.
  const RECENTS_KEY = '[cherenkov] recent_workspaces';
  const [recentWorkspaces, setRecentWorkspaces] = useState<WorkspaceId[]>(() => {
    try {
      const raw = JSON.parse(localStorage.getItem(RECENTS_KEY) || '[]');
      return Array.isArray(raw) ? (raw as WorkspaceId[]) : [];
    } catch {
      return [];
    }
  });

  React.useEffect(() => {
    const active = surfaceFromPath(location.pathname);
    setRecentWorkspaces((prev) => {
      const next = [active, ...prev.filter((w) => w !== active)].slice(0, 4);
      try {
        localStorage.setItem(RECENTS_KEY, JSON.stringify(next));
      } catch {
        /* storage full or blocked -- recents are a convenience, not core */
      }
      return next;
    });
  }, [location.pathname]);

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

  // N-1: breadcrumb trail for the current location.
  const breadcrumbTrail = useMemo(
    () => [{ label: SURFACE_TITLES[activeWorkspace].title }],
    [activeWorkspace]
  );

  // N-3: deep-link target, e.g. /triage?divergence=div_123.
  const deepLinkDivergence = useMemo(
    () => new URLSearchParams(location.search).get('divergence') || undefined,
    [location.search]
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

  // N-6: "?" keyboard map overlay
  const [showKeyboardMap, setShowKeyboardMap] = useState(false);

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
      <GlobalShortcuts
        onNewRun={() => handleSelectWorkspace('authoring')}
        onSearch={() => {}}
        onNavigate={handleSelectWorkspace}
        onShowHelp={() => setShowKeyboardMap(true)}
      />
      <ErrorBoundary>
        <div className="flex h-screen w-screen overflow-hidden bg-bg-base text-text-primary font-sans antialiased flex-col relative" id="cherenkov-app-core">
          {/* Skip link: the sidebar plus the journey stepper put ~15 controls
              ahead of the content on every page. */}
          <a
            href="#main-content"
            className="sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 focus:z-[100] focus:px-4 focus:py-2 focus:rounded-lg focus:bg-cyan-400 focus:text-bg-base focus:font-mono focus:text-xs focus:font-bold"
          >
            Skip to main content
          </a>

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
            recentWorkspaces={recentWorkspaces}
          />

          {showOnboarding && (
            <OnboardingWizard onComplete={handleCompleteOnboarding} onEnableDemo={handleEnableDemo} />
          )}

          {showTour && !showOnboarding && (
            <GuidedTour onClose={handleCloseTour} onNavigate={handleSelectWorkspace} />
          )}

          {!online && <OfflineOverlay checking={checking} onRetry={refresh} lastCheckedAt={lastCheckedAt} />}

          <KeyboardMapOverlay isOpen={showKeyboardMap} onClose={() => setShowKeyboardMap(false)} />
          {/* 1. App Header */}
          <AppHeader
            activeWorkspaceTitle={SURFACE_TITLES[activeWorkspace].title}
            activeWorkspaceSubtitle={SURFACE_TITLES[activeWorkspace].subtitle}
            selectedProjectId={selectedProjectId}
            onSelectProject={(id) => setSelectedProjectId(id)}
            tokenUsagePercent={tokenUsagePercent}
            totalSpentEstimated={totalSpentEstimated}
            online={online}
            navOpen={navDrawerOpen}
            onToggleNav={() => setNavDrawerOpen((v) => !v)}
          />

          {/* 1b. Breadcrumbs below the top bar (N-1) */}
          <Breadcrumbs trail={breadcrumbTrail} />

          {/* 2. Journey Stepper -- always-visible "where am I in the loop" rail.
              Its progress comes from the active run, not from the current page. */}
          <JourneyStepper
            activeWorkspace={activeWorkspace}
            onSelectWorkspace={handleSelectWorkspace}
            pendingReviewCount={reviewPendingCount}
            activeRunId={activeRunId}
          />

          {/* 3. Main Layout Body with NavigationBar & 5 Workspaces */}
          <div className="flex-1 flex overflow-hidden relative">
            {/* Backdrop for the mobile nav drawer. */}
            {navDrawerOpen && (
              <div
                className="fixed inset-0 bg-black/60 z-30 lg:hidden"
                onClick={() => setNavDrawerOpen(false)}
                aria-hidden="true"
              />
            )}

            <NavigationBar
              activeWorkspace={activeWorkspace}
              onSelectWorkspace={handleSelectWorkspace}
              pendingReviewCount={reviewPendingCount}
              onNewRun={() => handleSelectWorkspace('authoring')}
              mobileOpen={navDrawerOpen}
              onCloseMobile={() => setNavDrawerOpen(false)}
            />

            <main id="main-content" tabIndex={-1} className="flex-1 overflow-hidden h-full min-w-0">
              <Suspense fallback={<WorkspaceFallback />}>
                <Routes>
                  <Route
                    path="/dashboard"
                    element={
                      <DashboardWorkspace
                        onNavigateToTriage={() => handleSelectWorkspace('triage')}
                        onNavigate={handleSelectWorkspace}
                        activeRunId={activeRunId}
                      />
                    }
                  />
                  <Route
                    path="/authoring"
                    element={<AuthoringWorkspace onRunStarted={setActiveRunId} />}
                  />
                  <Route
                    path="/triage"
                    element={<TriageWorkspace initialDivergenceId={deepLinkDivergence} />}
                  />
                  <Route path="/intelligence" element={<IntelligenceWorkspace />} />
                  <Route path="/settings" element={<SettingsWorkspace />} />
                  <Route path="/enterprise" element={<EnterpriseWorkspace />} />
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
              </Suspense>
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
