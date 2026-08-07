/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

/**
 * The offline fallback journey, as pure data so it can be shared between the
 * shell and the parity spec that pins it to the shipped builtin journey.
 *
 * The backend compresses several engine steps onto one surface; each entry
 * below is that surface's first step, which is what the shell shows while the
 * server is unreachable. tests/qa/fallback-journey-parity.spec.ts compares
 * this against GET /api/v1/journeys so a change on the engine side surfaces
 * as a failing test instead of a silent offline/online disagreement.
 */
import type { WorkspaceId } from './types';

export interface FallbackStage {
  surface: WorkspaceId;
  label: string;
  blurb: string;
}

export const FALLBACK_STAGES: FallbackStage[] = [
  {
    surface: 'authoring',
    label: 'Generate',
    blurb: 'Bring a spec, get a test suite',
  },
  {
    surface: 'dashboard',
    label: 'Validate',
    blurb: 'Run it against the real API',
  },
  {
    surface: 'triage',
    label: 'Triage',
    blurb: 'Review what was flagged',
  },
  {
    surface: 'intelligence',
    label: 'Knowledge',
    blurb: 'See what Cherenkov learned',
  },
];
