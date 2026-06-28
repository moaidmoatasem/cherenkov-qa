/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState } from 'react';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import LoginPage from './components/LoginPage';
import Sidebar from './components/Sidebar';
import TopBar from './components/TopBar';
import ProjectsScreen from './components/ProjectsScreen';
import SetupScreen from './components/SetupScreen';
import PipelineScreen from './components/PipelineScreen';
import ReviewScreen from './components/ReviewScreen';
import HealingScreen from './components/HealingScreen';
import EjectScreen from './components/EjectScreen';
import SettingsScreen from './components/SettingsScreen';
import UiKitScreen from './components/UiKitScreen';
import CommandPalette from './components/CommandPalette';
import DivergencesScreen from './components/DivergencesScreen';
import OverviewScreen from './components/OverviewScreen';
import TruthMapScreen from './components/TruthMapScreen';
import AuthorScreen from './components/AuthorScreen';
import SignalsScreen from './components/SignalsScreen';
import MemoryScreen from './components/MemoryScreen';
import GovernanceScreen from './components/GovernanceScreen';
import ChatScreen from './components/ChatScreen';
import DeviceManagerScreen from './components/DeviceManagerScreen';
import MobileScreen from './components/MobileScreen';
import KnowledgeExplorerScreen from './components/KnowledgeExplorerScreen';
import SddDashboardScreen from './components/SddDashboardScreen';
import VerdictScreen from './screens/VerdictScreen';
import VisualRegressionScreen from './components/VisualRegressionScreen';
import ExplorerScreen from './components/ExplorerScreen';
import GlobalShortcuts from './components/GlobalShortcuts';
import { ErrorBoundary } from './components/ErrorBoundary';
import GuidedTour from './components/GuidedTour';
import { Drawer, OfflineOverlay } from './components/ui';
import { useToast } from './components/ui/Toast';
import OnboardingWizard from './components/OnboardingWizard';
import SetupWizard from './components/SetupWizard';

import { Project, EndpointRichness } from './types';
import { runPipeline, fetchProjects, fetchMetricsData, fetchReviewQueue } from './lib/api';
import { useHealth } from './lib/useHealth';
import { listenDesktop } from './lib/tauri';
import { BrowserRouter, useNavigate, useLocation } from 'react-router-dom';

function InnerApp() {
  const { authRequired, loading: authLoading, user, logout } = useAuth();
  const { toast } = useToast();
  const navigate = useNavigate();
  const location = useLocation();
  const activeTab = (location.pathname === '/' || location.pathname === '/index.html') ? 'projects' : location.pathname.replace(/^[/]+/, '');
  const setActiveTab = (tab: string) => {
    navigate(tab === 'projects' ? '/' : `/${tab}`);
  };
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null);
  const [status, setStatus] = useState<'Live' | 'Idle'>('Idle');
  const [activeSpecPath, setActiveSpecPath] = useState<string>('');
  const [projectContext, setProjectContext] = useState<{ specPath: string; targetUrl: string; projectName: string } | null>(null);

  React.useEffect(() => {
    fetchProjects().then(data => {
      setProjects(data);
      if (data.length > 0 && !selectedProjectId) setSelectedProjectId(data[0].id);
    });
  }, []);

  // Backend liveness — single source of truth for the honest offline state (#221).
  const { online, demoMode, checking, refresh, lastCheckedAt } = useHealth();

  // Desktop shell: re-probe health when the engine sidecar changes state.
  React.useEffect(() => {
    const subs = ['engine-healthy', 'engine-demo-mode', 'engine-stopped'].map(evt =>
      listenDesktop(evt, () => refresh())
    );
    return () => { subs.forEach(p => p.then(unlisten => unlisten())); };
  }, [refresh]);

  // Autonomy settings with local storage persistence
  const [autonomy, setAutonomyState] = useState<'Assisted' | 'Augmented' | 'Agentic'>(() => {
    const saved = localStorage.getItem('[copilot] autonomy');
    return (saved === 'Assisted' || saved === 'Augmented' || saved === 'Agentic') ? saved : 'Assisted';
  });

  const setAutonomy = (val: 'Assisted' | 'Augmented' | 'Agentic') => {
    setAutonomyState(val);
    localStorage.setItem('[copilot] autonomy', val);
  };

  // State to manage context live drawer visibility
  const [isLiveDrawerOpen, setIsLiveDrawerOpen] = useState(false);

  // Observability Token pool metrics — polled from real /api/v1/metrics
  const [tokenUsagePercent, setTokenUsagePercent] = useState(0);
  const [totalSpentEstimated, setTotalSpentEstimated] = useState(0);

  React.useEffect(() => {
    const poll = () => {
      fetchMetricsData()
        .then(data => {
          const { totalTokens, totalCost } = data.metrics;
          setTokenUsagePercent(Math.min(100, Math.round((totalTokens / 50000) * 100)));
          setTotalSpentEstimated(totalCost);
        })
        .catch(() => {
          // backend unreachable — keep previous values
        });
    };
    poll();
    const id = setInterval(poll, 30_000);
    return () => clearInterval(id);
  }, []);

  // Live review queue badge count — polled every 30s
  const [reviewPendingCount, setReviewPendingCount] = useState(0);
  React.useEffect(() => {
    const pollQueue = () => {
      fetchReviewQueue('pending')
        .then(items => setReviewPendingCount(Array.isArray(items) ? items.length : 0))
        .catch(() => { /* keep previous value on error */ });
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

  React.useEffect(() => {
    if (showTour && !['setup', 'projects', 'pipeline', 'review', 'eject'].includes(activeTab)) {
      handleCloseTour();
    }
  }, [activeTab, showTour]);

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
    } catch(e) {
      toast(`Demo enable failed: ${(e as Error).message}`, 'danger');
    }
  };

  const handlePilotRun = async () => {
    try {
      await runPipeline({ spec_path: 'stub/openapi.yaml', demo_mode: true });
      toast('Pilot run started', 'info');
    } catch (err) {
      toast('Pilot run failed: ' + (err as Error).message, 'danger');
    }
  };

  // Retrieve current active project configuration
  const currentProject = projects.find(p => p.id === selectedProjectId) || null;

  // Triggers spec setup configuration screen
  const handleNewRun = () => {
    setActiveTab('setup');
    setStatus('Idle');
  };

  // Called when the New Project Wizard finishes — lands user on Author tab pre-seeded with project context
  const handleProjectCreated = (project: any, specPath: string) => {
    setProjects(prev => {
      const exists = prev.find(p => p.id === project.id);
      return exists ? prev : [project, ...prev];
    });
    setSelectedProjectId(project.id);
    setProjectContext({
      specPath: specPath || project.spec_path || '',
      targetUrl: project.target_url || '',
      projectName: project.name,
    });
    setActiveTab('author');
  };

  // Triggers active pipeline execution monitor
  const handleStartPipeline = async (endpoints: EndpointRichness[], specPath: string, targetUrl?: string, authHeader?: string) => {
    setActiveSpecPath(specPath);
    setActiveTab('pipeline');
    setStatus('Live');

    try {
      await runPipeline({
        spec_path: specPath,
        target_url: targetUrl || 'http://localhost:8000',
        auth_header: authHeader || undefined,
      });
    } catch (err) {
      toast('Real backend generation launch failed, falling back to mock pipeline.', 'danger');
    }
  };

  // Called when character stream compiles and finishes writing
  const handleCompletePipeline = () => {
    setActiveTab('review');
    setStatus('Idle');
  };

  // update tokens in proportion to simulated character typing step
  const handleUpdateTokensSpent = (tokens: number, cost: number) => {
    // calculate a realistic limit percentage
    const percent = Math.min(100, Math.round((tokens / 50000) * 100));
    setTokenUsagePercent(percent);
    setTotalSpentEstimated(cost);
  };

  // Called when human-in-the-loop approves tests in review queue
  const handleUpdatePassRateAndCount = (testCount: number, approvedCount: number) => {
    if (!selectedProjectId) return;

    setProjects(prev => prev.map(p => {
      if (p.id === selectedProjectId) {
        const passPercent = Math.round((approvedCount / testCount) * 100);
        return {
          ...p,
          stats: {
            ...p.stats,
            testsCount: testCount,
            passRate: passPercent
          }
        };
      }
      return p;
    }));
  };

  // Decrement healing counts as suggestions are accepted/rejected
  const handleSuggestResolveCount = (count: number) => {
    if (!selectedProjectId) return;

    setProjects(prev => prev.map(p => {
      if (p.id === selectedProjectId) {
        return {
          ...p,
          stats: {
            ...p.stats,
            healingCount: count
          }
        };
      }
      return p;
    }));
  };

  const handleSelectProject = (id: string) => {
    setSelectedProjectId(id);
  };

  // Auth gate — show login page when auth is required and no valid session
  if (authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-bg-base text-text-secondary text-sm">
        Loading…
      </div>
    );
  }
  if (authRequired && !user) {
    return <LoginPage />;
  }

  return (
    <>
      <GlobalShortcuts onNewRun={handleNewRun} onSearch={() => {}} />
      <ErrorBoundary>
      <div className="flex h-screen w-screen overflow-hidden bg-bg-base text-text-primary font-sans antialiased relative" id="cherenkov-app-core">
        {/* Mesh Background Decoration */}
        <div className="absolute top-[-200px] left-[-200px] w-[600px] h-[600px] bg-cyan-500/15 rounded-full blur-[120px] pointer-events-none z-0" />
        <div className="absolute bottom-[-100px] right-[-100px] w-[500px] h-[500px] bg-blue-600/10 rounded-full blur-[100px] pointer-events-none z-0" />

        {/* Global Reachability Layer: Command Palette */}
        <CommandPalette
          onNavigate={setActiveTab}
          onNewRun={handleNewRun}
          projects={projects}
          onSelectProject={handleSelectProject}
        />

        {showOnboarding && (
          <OnboardingWizard
            onComplete={handleCompleteOnboarding}
            onEnableDemo={handleEnableDemo}
          />
        )}

        {showTour && !showOnboarding && (
          <GuidedTour
            onClose={handleCloseTour}
            onNavigate={setActiveTab}
          />
        )}

        {/* Honest backend-offline state (#221) — blocks interaction on stale/missing data */}
        {!online && <OfflineOverlay checking={checking} onRetry={refresh} lastCheckedAt={lastCheckedAt} />}

        {/* LEFT SIDEBAR CONTROLS */}
        <Sidebar
          activeTab={activeTab}
          setActiveTab={setActiveTab}
          onNewRun={handleNewRun}
          status={status}
          tokenUsagePercent={tokenUsagePercent}
          projects={projects}
          selectedProjectId={selectedProjectId}
          onSelectProject={handleSelectProject}
          reviewPendingCount={reviewPendingCount}
        />

        {/* RIGHT DISPLAY VIEWPORT PANEL FRAME */}
        <div className="flex-1 flex flex-col overflow-hidden h-full">
          {/* TOP STATUS CONTROL BAR */}
          <div className="relative">
            <TopBar
              currentProject={currentProject}
              status={status}
              activeTab={activeTab}
              totalSpentEstimated={totalSpentEstimated}
              autonomy={autonomy}
              setAutonomy={setAutonomy}
              onLiveClick={() => setIsLiveDrawerOpen(true)}
              demoMode={demoMode}
            />
            {authRequired && user && (
              <div className="absolute top-0 right-0 h-full flex items-center gap-2 pr-4 z-50">
                <span className="text-xs text-text-secondary">
                  {user.username}
                  <span className="ml-1 text-cyan-400 font-medium">[{user.role}]</span>
                </span>
                <button
                  onClick={logout}
                  className="text-xs text-text-muted hover:text-text-primary border border-border-subtle rounded px-2 py-0.5 hover:border-border-strong transition"
                >
                  Sign out
                </button>
              </div>
            )}
          </div>

          {/* MAIN BODY SWITCHBOARD SECTION */}
          <main className="flex-1 overflow-hidden h-full">
            {activeTab === 'projects' && (
              <ProjectsScreen
                projects={projects}
                selectedProjectId={selectedProjectId}
                onSelectProject={handleSelectProject}
                onNewRun={handleNewRun}
                onProjectCreated={handleProjectCreated}
              />
            )}

            {activeTab === 'setup' && (
              <SetupScreen
                onStartPipeline={handleStartPipeline}
              />
            )}

            {activeTab === 'setup-wizard' && <SetupWizard />}

            {activeTab === 'pipeline' && (
              <PipelineScreen
                onCompletePipeline={handleCompletePipeline}
                onUpdateTokensSpent={handleUpdateTokensSpent}
              />
            )}

            {activeTab === 'review' && (
              <ReviewScreen
                onUpdatePassRateAndCount={handleUpdatePassRateAndCount}
                autonomy={autonomy}
              />
            )}

            {activeTab === 'healing' && (
              <HealingScreen
                onSuggestResolveCount={handleSuggestResolveCount}
              />
            )}

            {activeTab === 'eject' && (
              <EjectScreen />
            )}

            {activeTab === 'settings' && (
              <SettingsScreen />
            )}

            {activeTab === 'ui-kit' && (
              <UiKitScreen />
            )}

            {activeTab === 'overview' && (
              <OverviewScreen
                onNewRun={handleNewRun}
                onPilotRun={handlePilotRun}
                onNavigate={setActiveTab}
              />
            )}

            {activeTab === 'truth-map' && (
              <TruthMapScreen
                onNavigate={setActiveTab}
              />
            )}

            {activeTab === 'divergences' && (
              <DivergencesScreen />
            )}

            {activeTab === 'explore' && (
              <ExplorerScreen />
            )}

            {activeTab === 'visual-regression' && (
              <VisualRegressionScreen />
            )}

            {activeTab === 'author' && (
              <AuthorScreen
                projectContext={projectContext}
                onStartPipeline={handleStartPipeline}
              />
            )}

            {activeTab === 'signals' && (
              <SignalsScreen />
            )}

            {activeTab === 'governance' && (
              <GovernanceScreen />
            )}

            {activeTab === 'memory' && (
              <MemoryScreen />
            )}

            {activeTab === 'devices' && (
              <DeviceManagerScreen />
            )}

            {activeTab === 'mobile' && (
              <MobileScreen />
            )}

            {activeTab === 'chat' && (
              <ChatScreen />
            )}

            {activeTab === 'knowledge' && (
              <KnowledgeExplorerScreen />
            )}

            {activeTab === 'sdd' && (
              <SddDashboardScreen />
            )}
            {activeTab === 'verdict' && (
              <VerdictScreen />
            )}
          </main>
        </div>

        {/* Live-Run Execution Drawer contextually hosting PipelineScreen */}
        <Drawer
          isOpen={isLiveDrawerOpen}
          onClose={() => setIsLiveDrawerOpen(false)}
          title="Live Execution Pipeline Monitor"
        >
          <div className="h-[75vh] flex flex-col">
            <PipelineScreen
              onCompletePipeline={() => {
                handleCompletePipeline();
                setIsLiveDrawerOpen(false);
              }}
              onUpdateTokensSpent={handleUpdateTokensSpent}
            />
          </div>
        </Drawer>

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
