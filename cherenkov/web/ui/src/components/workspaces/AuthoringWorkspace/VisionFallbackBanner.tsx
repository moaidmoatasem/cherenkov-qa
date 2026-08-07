/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Eye, ArrowRight } from 'lucide-react';
import { fetchOcrStatus } from '../../../lib/api';

/**
 * J1 Vision Fallback Banner. Backed by the real /api/v1/ocr/status endpoint:
 * it only appears when the OCR/VLM binary is actually installed. The copy is
 * deliberately precise about what the fallback does (re-review generated
 * tests via screen-scraping) rather than promising click-to-pick element
 * candidates that do not exist yet.
 */
export const VisionFallbackBanner: React.FC = () => {
  const navigate = useNavigate();
  const [status, setStatus] = useState<{
    installed: boolean;
    binary: string;
    version: string;
    error: string;
  } | null>(null);
  const [checked, setChecked] = useState(false);

  useEffect(() => {
    let alive = true;
    fetchOcrStatus()
      .then((s) => alive && setStatus(s))
      .catch(() => alive && setStatus(null))
      .finally(() => alive && setChecked(true));
    return () => {
      alive = false;
    };
  }, []);

  if (!checked || !status?.installed) return null;

  return (
    <div
      className="flex flex-col sm:flex-row sm:items-center gap-3 p-4 rounded-xl bg-amber-500/10 border border-amber-500/30"
      data-testid="vision-fallback-banner"
    >
      <Eye className="w-4 h-4 text-amber-400 shrink-0" />
      <div className="flex-1 min-w-0">
        <p className="text-xs font-mono font-semibold text-amber-400">
          Vision fallback available ({status.binary}
          {status.version ? ` ${status.version}` : ''})
        </p>
        <p className="text-[11px] text-text-muted mt-0.5">
          When the pipeline cannot confidently locate UI elements, OCR re-review can surface alternative candidates
          against the generated tests in the Triage workspace.
        </p>
      </div>
      <button
        onClick={() => navigate('/triage')}
        className="shrink-0 px-3 py-1.5 rounded-lg bg-amber-500/15 hover:bg-amber-500/25 text-amber-400 border border-amber-500/30 text-[11px] font-mono font-bold flex items-center gap-1.5 transition cursor-pointer"
        data-testid="btn-vision-fallback-triage"
      >
        Review in Triage <ArrowRight className="w-3 h-3" />
      </button>
    </div>
  );
};

export default VisionFallbackBanner;
