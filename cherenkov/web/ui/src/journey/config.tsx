/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

/**
 * The single source of truth for the app's information architecture.
 *
 * The nav, the journey stepper, the workspace titles and the command palette
 * used to keep four independent hardcoded copies of this, which drifted --
 * the palette still pointed at screens that had been deleted. They now all
 * derive from the journey the backend actually runs, served by
 * GET /api/v1/journeys.
 *
 * Presentation that the backend has no opinion about (which icon, which route
 * aliases) stays here, keyed by surface.
 */
import React, { createContext, useContext } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  LayoutDashboard,
  Sparkles,
  CheckSquare,
  Brain,
  Settings,
  Smartphone,
} from 'lucide-react';
import { fetchJourneys } from '../lib/api';
import type { JourneyCatalogue, JourneyDefinition, WorkspaceId } from './types';

export interface SurfaceChrome {
  icon: React.ComponentType<{ className?: string }>;
  /** Legacy paths kept working as redirects so old links do not 404. */
  aliases: string[];
}

export const SURFACE_CHROME: Record<WorkspaceId, SurfaceChrome> = {
  dashboard: {
    icon: LayoutDashboard,
    aliases: ['overview', 'verdict', 'truth-map', 'signals', 'coverage'],
  },
  authoring: { icon: Sparkles, aliases: ['author', 'setup', 'pipeline', 'explore'] },
  triage: {
    icon: CheckSquare,
    aliases: ['review', 'divergences', 'healing', 'spec-vs-reality'],
  },
  intelligence: { icon: Brain, aliases: ['chat', 'knowledge', 'sdd', 'memory'] },
  settings: {
    icon: Settings,
    aliases: ['projects', 'devices', 'eject', 'governance', 'ui-kit'],
  },
  mobile: { icon: Smartphone, aliases: [] },
};

/**
 * Surfaces that exist but are not part of the conformance loop. Kept out of
 * the journey definition on purpose: Mobile is a real, working capability, not
 * a step on the way to a verdict.
 */
export const OTHER_SURFACES: WorkspaceId[] = ['mobile'];

export const SURFACE_TITLES: Record<WorkspaceId, { title: string; subtitle: string }> = {
  dashboard: { title: 'Dashboard', subtitle: 'Is your API release-ready?' },
  authoring: { title: 'Generate Tests', subtitle: 'Turn a spec into a test suite' },
  triage: { title: 'Triage', subtitle: 'Confirm what the AI flagged' },
  intelligence: {
    title: 'Knowledge',
    subtitle: "What Cherenkov's learned about your API",
  },
  settings: { title: 'Settings', subtitle: 'Providers, hardware & access' },
  mobile: { title: 'Mobile', subtitle: 'Run & monitor a Maestro device pilot' },
};

/**
 * Used until the backend answers, and if it cannot be reached at all. It
 * mirrors the shipped builtin journey so the shell renders the same loop
 * offline as online -- a fallback that disagreed with the server would be
 * worse than none.
 */
export const FALLBACK_JOURNEY: JourneyDefinition = {
  id: 'api-conformance',
  version: 1,
  label: 'API conformance loop',
  description: '',
  steps: [],
  stages: [
    {
      surface: 'authoring',
      step: 1,
      label: 'Generate',
      blurb: 'Bring a spec, get a test suite',
      step_ids: [],
    },
    {
      surface: 'dashboard',
      step: 2,
      label: 'Validate',
      blurb: 'Run it against the real API',
      step_ids: [],
    },
    {
      surface: 'triage',
      step: 3,
      label: 'Triage',
      blurb: 'Review what was flagged',
      step_ids: [],
    },
    {
      surface: 'intelligence',
      step: 4,
      label: 'Knowledge',
      blurb: 'See what Cherenkov learned',
      step_ids: [],
    },
  ],
};

interface JourneyContextValue {
  journey: JourneyDefinition;
  catalogue: JourneyCatalogue | undefined;
  /** True while we are still showing the fallback rather than server truth. */
  isFallback: boolean;
}

const JourneyContext = createContext<JourneyContextValue>({
  journey: FALLBACK_JOURNEY,
  catalogue: undefined,
  isFallback: true,
});

export function JourneyProvider({ children }: { children: React.ReactNode }) {
  const { data } = useQuery({
    queryKey: ['journeys'],
    queryFn: fetchJourneys,
    staleTime: 5 * 60_000, // definitions change on deploy, not per interaction
  });

  const journey =
    data?.journeys.find((j) => j.id === data.default) ??
    data?.journeys[0] ??
    FALLBACK_JOURNEY;

  return (
    <JourneyContext.Provider
      value={{ journey, catalogue: data, isFallback: !data }}
    >
      {children}
    </JourneyContext.Provider>
  );
}

export function useJourney(): JourneyContextValue {
  return useContext(JourneyContext);
}

/** The loop's surfaces, in the order the journey runs them. */
export function useJourneySurfaces(): WorkspaceId[] {
  const { journey } = useJourney();
  return journey.stages.map((s) => s.surface);
}

/** Nav order: the loop, then Settings, which is not a step in it. */
export function useNavSurfaces(): WorkspaceId[] {
  const loop = useJourneySurfaces();
  return [...loop, 'settings' as WorkspaceId].filter(
    (s, i, all) => all.indexOf(s) === i
  );
}

/** Resolve a URL path to a surface, honouring legacy aliases. */
export function surfaceFromPath(pathname: string): WorkspaceId {
  const path = pathname.replace(/^[/]+/, '').replace(/[/]+$/, '');
  if (!path || path === 'index.html') return 'dashboard';
  const surfaces = Object.keys(SURFACE_CHROME) as WorkspaceId[];
  if (surfaces.includes(path as WorkspaceId)) return path as WorkspaceId;
  for (const surface of surfaces) {
    if (SURFACE_CHROME[surface].aliases.includes(path)) return surface;
  }
  return 'dashboard';
}
