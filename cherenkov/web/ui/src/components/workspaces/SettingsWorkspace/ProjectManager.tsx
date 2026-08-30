/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState, useEffect } from 'react';
import { Card, Skeleton } from '../../ui';
import { fetchProjects, createProject } from '../../../lib/api';
import { Project } from '../../../types';
import { FolderGit2, Plus, RefreshCw, CheckCircle2 } from 'lucide-react';

export const ProjectManager: React.FC = () => {
  const [projects, setProjects] = useState<Project[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [newName, setNewName] = useState('');
  const [newTargetUrl, setNewTargetUrl] = useState('http://localhost:8000');
  const [newSpecPath, setNewSpecPath] = useState('');

  const loadProjects = async () => {
    try {
      setIsLoading(true);
      setError(null);
      const data = await fetchProjects();
      setProjects(data || []);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadProjects();
  }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newName.trim()) return;
    try {
      await createProject({
        name: newName.trim(),
        target_url: newTargetUrl,
        spec_path: newSpecPath,
      });
      setNewName('');
      setShowCreate(false);
      loadProjects();
    } catch (err) {
      setError((err as Error).message);
    }
  };

  return (
    <Card className="p-6 space-y-4" data-testid="project-manager">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold font-mono uppercase tracking-wider text-text-muted flex items-center gap-2">
            <FolderGit2 className="w-4 h-4 text-cyan-400" />
            <span>Workspace & Project Manager</span>
          </h2>
          <p className="text-xs text-text-muted mt-0.5">
            The projects and target APIs this instance knows about.
          </p>
        </div>
        <button
          onClick={() => setShowCreate(!showCreate)}
          className="px-3 py-1.5 bg-cyan-500/20 text-cyan-400 border border-cyan-500/30 rounded-lg text-xs font-mono font-bold flex items-center gap-1"
          data-testid="btn-create-project-toggle"
        >
          <Plus className="w-3.5 h-3.5" /> {showCreate ? 'Cancel' : 'New Project'}
        </button>
      </div>

      {showCreate && (
        <form onSubmit={handleCreate} className="p-4 bg-black/30 border border-white/10 rounded-xl space-y-3 font-mono text-xs">
          <div className="space-y-1">
            <label className="text-[10px] text-text-muted uppercase">Project Name</label>
            <input
              type="text"
              required
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              placeholder="e.g. Payment Gateway Service"
              className="w-full bg-bg-base text-text-primary p-2 rounded-lg border border-white/10"
              data-testid="input-new-project-name"
            />
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div className="space-y-1">
              <label className="text-[10px] text-text-muted uppercase">Target Host URL</label>
              <input
                type="text"
                value={newTargetUrl}
                onChange={(e) => setNewTargetUrl(e.target.value)}
                className="w-full bg-bg-base text-text-primary p-2 rounded-lg border border-white/10"
              />
            </div>
            <div className="space-y-1">
              <label className="text-[10px] text-text-muted uppercase">Spec Path</label>
              <input
                type="text"
                value={newSpecPath}
                onChange={(e) => setNewSpecPath(e.target.value)}
                placeholder="cherenkov/stub/openapi.yaml"
                className="w-full bg-bg-base text-text-primary p-2 rounded-lg border border-white/10"
              />
            </div>
          </div>
          <button
            type="submit"
            className="px-4 py-2 bg-cyan-500 text-slate-950 font-bold rounded-lg text-xs"
            data-testid="btn-submit-create-project"
          >
            Create Workspace Project
          </button>
        </form>
      )}

      {isLoading ? (
        <Skeleton className="h-24 w-full rounded-xl" />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 font-mono text-xs">
          {projects.map((p) => (
            <div key={p.id} className="p-3 rounded-xl bg-black/20 border border-white/5 space-y-1">
              <div className="flex items-center justify-between">
                <span className="font-bold text-text-primary">{p.name}</span>
                <span className="text-[10px] text-emerald-400">{p.stats?.passRate ?? 100}% Pass</span>
              </div>
              <p className="text-[10px] text-text-muted">ID: {p.id}</p>
              <p className="text-[10px] text-text-muted">Tests: {p.stats?.testsCount || 0}</p>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
};

export default ProjectManager;
