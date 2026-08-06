/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import { useEffect } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { fetchJourneyRun } from '../lib/api';
import { useLiveEvents } from '../hooks/useLiveEvents';
import type { JourneyRunState } from './types';

/**
 * Live state for one run.
 *
 * Polling and the WebSocket are both used on purpose. The socket makes updates
 * immediate; the poll means a client that connected late, dropped, or missed a
 * broadcast still converges on the truth instead of showing a stepper frozen
 * at whatever it last heard.
 */
export function useJourneyRun(runId: string | null) {
  const queryClient = useQueryClient();

  const query = useQuery<JourneyRunState>({
    queryKey: ['journey-run', runId],
    queryFn: () => fetchJourneyRun(runId as string),
    enabled: !!runId,
    // Stop polling once the run reaches a terminal state.
    refetchInterval: (q) =>
      q.state.data && q.state.data.status !== 'running' ? false : 3000,
  });

  const { lastEvent, connected } = useLiveEvents();

  useEffect(() => {
    if (!runId || !lastEvent) return;
    const type = lastEvent.type;
    if (
      type === 'step_state' ||
      type === 'stage_success' ||
      type === 'pipeline_complete'
    ) {
      queryClient.invalidateQueries({ queryKey: ['journey-run', runId] });
    }
  }, [lastEvent, runId, queryClient]);

  return { ...query, live: connected };
}
