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
import { ToastProvider, Drawer, EmptyState } from './components/ui';

import { Project, EndpointRichness } from './types';
import { INITIAL_PROJECTS } from './mockData';
import { runPipeline } from './lib/api';

export default function App() {
  const [activeTab, setActiveTab] = useState<string>('projects');
  const [projects, setProjects] = useState<Project[]>(INITIAL_PROJECTS);
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>('proj-petstore');
  const [status, setStatus] = useState<'Live' | 'Idle'>('Idle');
  const [activeSpecPath, setActiveSpecPath] = useState<string>('');
  
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
      console.warn('Real backend generation launch failed, falling back to mock pipeline', err);
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
    <ToastProvider>
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

            {/* PLACEHOLDER SCREENS */}
            {activeTab === 'overview' && (
              <div className="p-6">
                <EmptyState
                  title="Overview (Landing)"
                  description="Coming in this milestone. This screen will display Release Readiness KPIs, top active divergences, and Reflector learning activity feeds."
                  primaryAction={{
                    label: 'Run Discovery Scan',
                    onClick: handleNewRun
                  }}
                />
              </div>
            )}

            {activeTab === 'truth-map' && (
              <div className="p-6">
                <EmptyState
                  title="Truth Map"
                  description="Coming in this milestone. This screen will display the endpoint claims graph generated from traffic, specifications, and databases."
                  primaryAction={{
                    label: 'Define Claims Mapping',
                    onClick: () => {}
                  }}
                />
              </div>
            )}

            {activeTab === 'divergences' && (
              <div className="p-6">
                <EmptyState
                  title="Divergences Triage"
                  description="Coming in this milestone. This flagship triage view will list confirmed API drifts, request/response diffs, and validation status updates."
                  primaryAction={{
                    label: 'Inspect Active Mismatches',
                    onClick: () => {}
                  }}
                />
              </div>
            )}

            {activeTab === 'explore' && (
              <div className="p-6">
                <EmptyState
                  title="Explore Crawler"
                  description="Coming in this milestone. This autonomous crawler will perform automated page crawling to discover runtime anomalies and browser logs."
                  primaryAction={{
                    label: 'Configure Scope & Targets',
                    onClick: () => {}
                  }}
                />
              </div>
            )}

            {activeTab === 'author' && (
              <div className="p-6">
                <EmptyState
                  title="Author by Intent"
                  description="Coming in this milestone. This natural language dialog copilot interface will let you write Playwright test scenarios with Mentor idiom recommendations."
                  primaryAction={{
                    label: 'Compose Test Scenario',
                    onClick: () => {}
                  }}
                />
              </div>
            )}

            {activeTab === 'signals' && (
              <div className="p-6">
                <EmptyState
                  title="Telemetry Signals"
                  description="Coming in this milestone. This view will organize test coverage, visual comparison regressions, and API endpoint performance graphs in tabs."
                  primaryAction={{
                    label: 'Connect Telemetry Streams',
                    onClick: () => {}
                  }}
                />
              </div>
            )}

            {activeTab === 'governance' && (
              <div className="p-6">
                <EmptyState
                  title="Governance & certification"
                  description="Coming in this milestone. This board will track model faithfulness certifications, prompt regression checks, and compliance compliance reports."
                  primaryAction={{
                    label: 'Download Audit Log',
                    onClick: () => {}
                  }}
                />
              </div>
            )}

            {activeTab === 'memory' && (
              <div className="p-6">
                <EmptyState
                  title="Reflector Memory & Pairing"
                  description="Coming in this milestone. This screen will visualize accumulated senior testing idioms and Mentor pairing guidelines for junior developers."
                  primaryAction={{
                    label: 'Manage Verdict Memory',
                    onClick: () => {}
                  }}
                />
              </div>
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
    </ToastProvider>
  );
}
