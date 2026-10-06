/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React from 'react';
import { Info } from 'lucide-react';

/**
 * Shown when the findings on screen are the built-in demo corpus, not results
 * from the user's own run. A verdict nobody measured must not look like one.
 */
export const SampleDataBanner: React.FC = () => (
  <div
    data-testid="sample-data-banner"
    role="note"
    className="flex items-center gap-2 rounded border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs text-amber-300"
  >
    <Info className="w-4 h-4 shrink-0" aria-hidden="true" />
    <span>
      Sample findings (built-in demo data). Run <code className="font-mono">cherenkov verify</code> to see yours.
    </span>
  </div>
);

export const hasSampleData = (items: ReadonlyArray<{ sample?: boolean }>): boolean =>
  items.some((i) => i.sample === true);
