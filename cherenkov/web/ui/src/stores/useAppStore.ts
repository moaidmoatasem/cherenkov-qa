import { create } from 'zustand';
import { Project } from '../types';

export interface AppState {
  activeTab: string;
  projects: Project[];
  selectedProjectId: string | null;
  status: 'Live' | 'Idle';
  autonomy: 'Assisted' | 'Augmented' | 'Agentic';
  tokenUsagePercent: number;
  totalSpentEstimated: number;
  recentProjects: string[];
  
  setActiveTab: (tab: string) => void;
  setProjects: (projects: Project[]) => void;
  setSelectedProjectId: (id: string | null) => void;
  setStatus: (status: 'Live' | 'Idle') => void;
  setAutonomy: (val: 'Assisted' | 'Augmented' | 'Agentic') => void;
  setTokenUsagePercent: (percent: number) => void;
  setTotalSpentEstimated: (cost: number) => void;
  addRecentProject: (id: string) => void;
}

export const useAppStore = create<AppState>((set) => ({
  activeTab: 'projects',
  projects: [],
  selectedProjectId: null,
  status: 'Idle',
  autonomy: 'Assisted',
  tokenUsagePercent: 0,
  totalSpentEstimated: 0,
  recentProjects: [],

  setActiveTab: (tab) => set({ activeTab: tab }),
  setProjects: (projects) => set({ projects }),
  setSelectedProjectId: (id) => set({ selectedProjectId: id }),
  setStatus: (status) => set({ status }),
  setAutonomy: (val) => set({ autonomy: val }),
  setTokenUsagePercent: (percent) => set({ tokenUsagePercent: Math.min(100, Math.max(0, percent)) }),
  setTotalSpentEstimated: (cost) => set({ totalSpentEstimated: cost }),
  addRecentProject: (id) => set((state) => {
    const without = state.recentProjects.filter(p => p !== id);
    return { recentProjects: [id, ...without].slice(0, 5) };
  }),
}));
