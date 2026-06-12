/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState } from 'react';
import { 
  FolderGit2, 
  Plus, 
  TrendingUp, 
  Calendar, 
  CircleDot, 
  Search, 
  Stethoscope, 
  CheckCircle2, 
  AlertTriangle,
  Timer
} from 'lucide-react';
import { Project } from '../types';
import CherenkovLogo from './CherenkovLogo';

interface ProjectsScreenProps {
  projects: Project[];
  selectedProjectId: string | null;
  onSelectProject: (id: string) => void;
  onNewRun: () => void;
}

export default function ProjectsScreen({
  projects,
  selectedProjectId,
  onSelectProject,
  onNewRun
}: ProjectsScreenProps) {
  const [searchTerm, setSearchTerm] = useState('');

  const filteredProjects = projects.filter(p => 
    p.name.toLowerCase().includes(searchTerm.toLowerCase())
  );

  // Sparkline builder converts score array to elegant path coordinate strings
  const getSparklinePath = (data: number[], width: number, height: number) => {
    if (data.length < 2) return '';
    const min = Math.min(...data);
    const max = Math.max(...data);
    const range = max - min === 0 ? 1 : max - min;
    const xStep = width / (data.length - 1);
    
    return data.map((val, idx) => {
      const x = idx * xStep;
      // Invert Y so higher number is closer to top (0)
      const y = height - ((val - min) / range) * (height - 8) - 4;
      return `${idx === 0 ? 'M' : 'L'} ${x} ${y}`;
    }).join(' ');
  };

  const statusColorMap = {
    done: 'bg-[#3FB950]',
    running: 'bg-glow-blue animate-pulse cherenkov-glow',
    queued: 'bg-gray-brand',
    failed: 'bg-[#F85149]'
  };

  return (
    <div className="p-8 h-full overflow-y-auto space-y-8 grid-bg bg-transparent flex flex-col relative z-10" id="projects-screen">

      {/* Intro Header Row */}
      <div className="flex items-start justify-between flex-wrap gap-4">
        <div className="flex items-center gap-4">
          <CherenkovLogo variant="icon" size={42} />
          <div>
            <h1 className="font-display font-bold text-3xl text-text-primary tracking-tight">
              Cherenkov Observability Root
            </h1>
            <p className="text-sm text-text-muted mt-1 font-sans">
              Localhost testing particles. Real-time agent code-generation analytics.
            </p>
          </div>
        </div>
        
        {/* New Run Button */}
        <button
          onClick={onNewRun}
          id="btn-projects-new-run"
          className="flex items-center gap-2 px-5 py-2.5 rounded-md bg-glow-blue hover:bg-opacity-90 text-slate-950 text-sm font-semibold transition-all duration-300 shadow-lg shadow-cyan-500/20"
        >
          <Plus className="w-4 h-4 text-slate-950 stroke-[3px]" />
          <span>New Validation Run</span>
        </button>
      </div>

      {/* Quick Search & Filters Bar */}
      <div className="flex items-center gap-4 bg-white/5 backdrop-blur-xl border border-white/10 p-4 rounded-xl">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-2.5 w-4.5 h-4.5 text-text-muted" />
          <input
            type="text"
            placeholder="Search API workspaces..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            id="workspace-search-input"
            className="w-full bg-black/20 text-text-primary placeholder:text-text-muted/65 text-sm pl-11 pr-4 py-2 rounded border border-white/10 focus:outline-none focus:border-glow-blue focus:ring-1 focus:ring-glow-blue transition"
          />
        </div>
        <div className="flex items-center gap-2 text-xs font-mono text-text-muted">
          <span>Active Registry Count:</span>
          <span className="text-glow-bright font-bold font-sans text-sm">{filteredProjects.length}</span>
        </div>
      </div>

      {/* Empty State */}
      {filteredProjects.length === 0 ? (
        <div className="flex-1 flex flex-col items-center justify-center py-20 bg-white/5 backdrop-blur-xl border border-dashed border-white/10 rounded-2xl">
          <div className="mb-4">
            <CherenkovLogo variant="wireframe" size={54} glow={false} />
          </div>
          <h3 className="text-xl font-display font-medium text-text-primary">No workspace projects found</h3>
          <p className="text-text-muted text-sm mt-1 max-w-md text-center">
            Upload an OpenAPI Swagger blueprint to index automatic diagnostic testing gates.
          </p>
          <div className="mt-8 font-mono italic text-glow-bright text-xs tracking-widest uppercase">
            "See your tests being born."
          </div>
          <button
            onClick={onNewRun}
            className="mt-6 px-4 py-2 rounded bg-accent-bg border border-glow-blue text-glow-bright text-sm hover:bg-glow-blue hover:text-bg-base transition duration-300"
          >
            Create Your First Run
          </button>
        </div>
      ) : (
        /* Workspaces Grid list */
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredProjects.map((project) => {
            const isSelected = selectedProjectId === project.id;
            const sparkPoints = project.sparkline;
            const sparkWidth = 140;
            const sparkHeight = 36;
            
            return (
              <div
                key={project.id}
                onClick={() => onSelectProject(project.id)}
                id={`project-card-${project.id}`}
                className={`group cursor-pointer rounded-2xl p-5 border transition-all duration-300 relative flex flex-col justify-between ${
                  isSelected 
                    ? 'bg-white/10 backdrop-blur-xl border-glow-blue/85 cherenkov-glow shadow-lg shadow-cyan-500/10' 
                    : 'bg-white/5 backdrop-blur-md border-white/10 hover:border-glow-blue/50 hover:bg-white/10'
                }`}
              >
                {/* Active Indicator Flare */}
                {isSelected && (
                  <div className="absolute top-0 left-10 right-10 h-[2px] bg-glow-blue shadow-[0_0_15px_#22d3ee]" />
                )}

                <div>
                  {/* Name and Last Run */}
                  <div className="flex justify-between items-start mb-3">
                    <div>
                      <h3 className="font-display font-semibold text-[17px] text-text-primary group-hover:text-glow-bright transition duration-200">
                        {project.name}
                      </h3>
                      <div className="flex items-center gap-1.5 text-[11px] text-text-muted mt-1 font-mono">
                        <Calendar className="w-3 h-3 text-gray-brand" />
                        <span>Run: {project.lastRun}</span>
                      </div>
                    </div>
                    {/* Tiny Status Dot Strip */}
                    <div className="flex gap-1.5 p-1.5 rounded bg-black/40 border border-white/5" title="Pipeline Status Index">
                      <span className={`w-2.5 h-2.5 rounded-full ${statusColorMap[project.pipelineStatus.ingest]}`} title="Ingest" />
                      <span className={`w-2.5 h-2.5 rounded-full ${statusColorMap[project.pipelineStatus.plan]}`} title="Plan" />
                      <span className={`w-2.5 h-2.5 rounded-full ${statusColorMap[project.pipelineStatus.generate]}`} title="Generate" />
                      <span className={`w-2.5 h-2.5 rounded-full ${statusColorMap[project.pipelineStatus.review]}`} title="Review" />
                      {project.pipelineStatus.visual && (
                        <span className={`w-2.5 h-2.5 rounded-full ${statusColorMap[project.pipelineStatus.visual]}`} title="Visual E2E" />
                      )}
                      {project.pipelineStatus.perf && (
                        <span className={`w-2.5 h-2.5 rounded-full ${statusColorMap[project.pipelineStatus.perf]}`} title="Performance" />
                      )}
                    </div>
                  </div>

                  {/* Execution Timer Progress Bar */}
                  {project.lastRunDuration && (() => {
                    const { durationMs, limitMs } = project.lastRunDuration;
                    const percent = Math.min(100, Math.round((durationMs / limitMs) * 100));
                    const seconds = (durationMs / 1000).toFixed(1);
                    const limitSec = (limitMs / 1000).toFixed(0);
                    
                    const isSlaCritical = percent > 85;
                    const barColorClass = isSlaCritical 
                      ? 'bg-gradient-to-r from-amber-500 to-red-500 shadow-[0_0_8px_rgba(239,68,68,0.4)]'
                      : 'bg-gradient-to-r from-cyan-400 to-glow-blue shadow-[0_0_8px_rgba(6,182,212,0.4)]';

                    return (
                      <div className="mt-2.5 mb-3 p-2 bg-black/25 rounded-xl border border-white/5 space-y-1 font-mono text-[10px]" id={`timer-bar-${project.id}`}>
                        <div className="flex items-center justify-between text-[#7D8DA1]/90">
                          <div className="flex items-center gap-1.5">
                            <Timer className="w-3.5 h-3.5 text-glow-blue animate-pulse-slow" />
                            <span className="font-semibold uppercase tracking-wider text-[9px] text-[#7D8DA1]/85">Last Run Duration</span>
                          </div>
                          <span className={`font-bold text-[10px] ${isSlaCritical ? 'text-amber-400' : 'text-glow-bright'}`}>
                            {seconds}s <span className="text-[#334C5A]">/ {limitSec}s SLA</span>
                          </span>
                        </div>
                        {/* Track */}
                        <div className="w-full bg-white/5 rounded-full h-1 overflow-hidden border border-white/5">
                          <div 
                            className={`h-full rounded-full transition-all duration-1000 ${barColorClass}`}
                            style={{ width: `${percent}%` }}
                          />
                        </div>
                        <div className="flex justify-between text-[8px] text-[#334C5A] uppercase tracking-widest leading-none pt-0.5">
                          <span>0s</span>
                          <span>{limitSec}s peak</span>
                        </div>
                      </div>
                    );
                  })()}

                  {/* Stats Badging Grid */}
                  <div className="grid grid-cols-3 gap-2 my-4 bg-black/30 p-3 rounded border border-white/5 font-mono text-[11px]">
                    <div>
                      <span className="block text-[9px] text-[#7D8DA1]/85 uppercase">Tests</span>
                      <span className="text-sm font-semibold font-sans text-text-primary">{project.stats.testsCount}</span>
                    </div>
                    <div>
                      <span className="block text-[9px] text-[#7D8DA1]/85 uppercase">Pass Rate</span>
                      <span className={`text-sm font-semibold font-sans ${
                        project.stats.passRate >= 90 ? 'text-success-custom' : 
                        project.stats.passRate >= 70 ? 'text-warning-custom' : 'text-danger-custom'
                      }`}>
                        {project.stats.passRate}%
                      </span>
                    </div>
                    <div>
                      <span className="block text-[9px] text-[#7D8DA1]/85 uppercase">Healing</span>
                      <span className={`text-sm font-semibold font-sans ${project.stats.healingCount > 0 ? 'text-glow-bright' : 'text-text-muted'}`}>
                        {project.stats.healingCount} SUGG
                      </span>
                    </div>
                  </div>
                </div>

                {/* Sparkling pass rate visualizer */}
                <div className="flex items-end justify-between pt-2 border-t border-border-custom/40 mt-2">
                  <div className="flex items-center gap-1.5">
                    <TrendingUp className="w-3.5 h-3.5 text-success-custom" />
                    <span className="text-[10px] text-text-muted font-mono tracking-wide">Pass-rate Trend</span>
                  </div>

                  {/* Sparkline canvas */}
                  <svg width={sparkWidth} height={sparkHeight} className="overflow-visible">
                    <path
                      d={getSparklinePath(sparkPoints, sparkWidth, sparkHeight)}
                      fill="none"
                      stroke="#2D9CDB"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      className="drop-shadow-[0_0_4px_rgba(45,156,219,0.5)]"
                    />
                    {/* End glowing marker point */}
                    {sparkPoints.length > 0 && (
                      <circle
                        cx={sparkWidth}
                        cy={sparkHeight - ((sparkPoints[sparkPoints.length - 1] - Math.min(...sparkPoints)) / (Math.max(...sparkPoints) - Math.min(...sparkPoints) === 0 ? 1 : Math.max(...sparkPoints) - Math.min(...sparkPoints))) * (sparkHeight - 8) - 4}
                        r="3.5"
                        className="fill-glow-bright stroke-bg-base stroke-2 animate-pulse"
                      />
                    )}
                  </svg>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Slogan Banner footer */}
      {filteredProjects.length > 0 && (
        <div className="mt-auto py-6 border-t border-border-custom/30 text-center">
          <p className="font-mono text-xs tracking-[0.25em] text-[#334C5A] uppercase select-none">
            "See your tests being born."
          </p>
        </div>
      )}
    </div>
  );
}
