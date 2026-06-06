/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState } from 'react';
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
import GuidedTour from './components/GuidedTour';
import { Drawer, OfflineOverlay } from './components/ui';
import { useToast } from './components/ui/Toast';

import { Project, EndpointRichness } from './types';
import { runPipeline, fetchProjects } from './lib/api';
import { useHealth } from './lib/useHealth';

export default function App() {
  const { toast } = useToast();
  const [activeTab, setActiveTab] = useState<string>('projects');
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null);
  const [status, setStatus] = useState<'Live' | 'Idle'>('Idle');
  const [activeSpecPath, setActiveSpecPath] = useState<string>('');

  React.useEffect(() => {
    fetchProjects().then(data => {
      setProjects(data);
      if (data.length > 0 && !selectedProjectId) setSelectedProjectId(data[0].id);
    });
  }, []);

  // Backend liveness — single source of truth for the honest offline state (#221).
  const { online, demoMode, checking, refresh } = useHealth();

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

  // Observability Token pool metric simulations
  const [tokenUsagePercent, setTokenUsagePercent] = useState(43);
  const [totalSpentEstimated, setTotalSpentEstimated] = useState(0.14);

  // Guided Tour state
  const [showTour, setShowTour] = useState(() => {
    return localStorage.getItem('[copilot] tour_seen') !== 'true';
  });

  const handleCloseTour = () => {
    setShowTour(false);
    localStorage.setItem('[copilot] tour_seen', 'true');
  };

  // Retrieve current active project configuration
  const currentProject = projects.find(p => p.id === selectedProjectId) || null;

  // Triggers spec setup configuration screen
  const handleNewRun = () => {
    setActiveTab('setup');
    setStatus('Idle');
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

  // Select project ID and load active variables
  const handleSelectProject = (id: string) => {
    setSelectedProjectId(id);
    const proj = projects.find(p => p.id === id);
    if (proj) {
      // simulate localized cost values proportional to previous run counts
      setTotalSpentEstimated(proj.stats.testsCount * 0.0034);
      setTokenUsagePercent(Math.min(95, Math.round(proj.stats.testsCount * 1.5)));
    }
  };

  return (
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

        {showTour && (
          <GuidedTour 
            onClose={handleCloseTour} 
            onNavigate={setActiveTab} 
          />
        )}

        {/* Honest backend-offline state (#221) — blocks interaction on stale/missing data */}
        {!online && <OfflineOverlay checking={checking} onRetry={refresh} />}

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
        />

        {/* RIGHT DISPLAY VIEWPORT PANEL FRAME */}
        <div className="flex-1 flex flex-col overflow-hidden h-full">
          {/* TOP STATUS CONTROL BAR */}
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

          {/* MAIN BODY SWITCHBOARD SECTION */}
          <main className="flex-1 overflow-hidden h-full">
            {activeTab === 'projects' && (
              <ProjectsScreen
                projects={projects}
                selectedProjectId={selectedProjectId}
                onSelectProject={handleSelectProject}
                onNewRun={handleNewRun}
              />
            )}

            {activeTab === 'setup' && (
              <SetupScreen
                onStartPipeline={handleStartPipeline}
              />
            )}

            {activeTab === 'pipeline' && (
              <PipelineScreen
                onCompletePipeline={handleCompletePipeline}
                onUpdateTokensSpent={handleUpdateTokensSpent}
              />
            )}

            {activeTab === 'review' && (
              <ReviewScreen
                onUpdatePassRateAndCount={handleUpdatePassRateAndCount}
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
              <div className="p-6">
                <div className="bg-white/5 border border-white/10 rounded-2xl p-8 max-w-lg mx-auto text-center space-y-4">
                  <h3 className="font-display font-semibold text-lg text-text-primary">Explore Crawler</h3>
                  <p className="text-xs text-[#7D8DA1] leading-relaxed">
                    This autonomous crawler parses specifications to execute live crawling runs, diagnosing anomalies and front-end errors.
                  </p>
                  <button
                    onClick={handleNewRun}
                    className="px-6 py-2 bg-glow-blue hover:bg-opacity-95 text-slate-950 font-bold text-xs rounded-xl uppercase font-mono tracking-wider transition cursor-pointer"
                  >
                    Configure Scope & Target
                  </button>
                </div>
              </div>
            )}

            {activeTab === 'author' && (
              <AuthorScreen />
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
  );
}
