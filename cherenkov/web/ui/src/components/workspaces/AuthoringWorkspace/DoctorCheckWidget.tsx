/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useEffect, useState } from 'react';
import { Card, Skeleton } from '../../ui';
import { fetchDoctor, DoctorCheck } from '../../../lib/api';
import { Stethoscope, CheckCircle2, AlertTriangle, XCircle, RefreshCw } from 'lucide-react';

export const DoctorCheckWidget: React.FC = () => {
  const [checks, setChecks] = useState<DoctorCheck[]>([]);
  const [ready, setReady] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const runDoctor = async () => {
    try {
      setIsLoading(true);
      setError(null);
      const data = await fetchDoctor();
      setChecks(data.checks || []);
      setReady(data.ready);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    runDoctor();
  }, []);

  return (
    <Card className="p-6 space-y-4" data-testid="doctor-check-widget">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold font-mono uppercase tracking-wider text-text-muted flex items-center gap-2">
            <Stethoscope className="w-4 h-4 text-cyan-400" />
            <span>OpenAPI & System Doctor Check</span>
          </h2>
          <p className="text-xs text-text-muted mt-0.5">
            Whether this machine has what it needs to generate and run tests.
          </p>
        </div>
        <button
          onClick={runDoctor}
          className="p-1.5 rounded-lg border border-border-subtle hover:border-border-strong text-text-muted hover:text-text-primary transition"
          title="Run Doctor Checks"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {error ? (
        <div className="p-3 bg-rose-500/10 border border-rose-500/30 rounded-xl text-xs text-rose-400">
          Doctor check failed: {error}
        </div>
      ) : (
        <div className="space-y-3">
          <div
            className={`p-3 rounded-xl border flex items-center justify-between text-xs font-mono font-bold ${
              ready && !isLoading
                ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
                : 'bg-amber-500/10 border-amber-500/30 text-amber-400'
            }`}
          >
            <span>ENGINE READINESS STATUS:</span>
            <span>{isLoading ? 'CHECKING...' : ready ? 'READY TO GENERATE' : 'CHECKS REQUIRED'}</span>
          </div>

          {isLoading ? (
            <div className="space-y-2">
              <Skeleton className="h-10 w-full rounded-lg" />
              <Skeleton className="h-10 w-full rounded-lg" />
            </div>
          ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {checks.map((chk) => (
              <div
                key={chk.id || chk.name}
                className="p-3 rounded-xl bg-black/20 border border-white/5 flex items-start gap-3 text-xs"
              >
                {chk.status === 'passed' ? (
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 mt-0.5 shrink-0" />
                ) : chk.status === 'warning' ? (
                  <AlertTriangle className="w-4 h-4 text-amber-400 mt-0.5 shrink-0" />
                ) : (
                  <XCircle className="w-4 h-4 text-rose-400 mt-0.5 shrink-0" />
                )}
                <div>
                  <p className="font-mono font-bold text-text-primary">{chk.name}</p>
                  {chk.message && <p className="text-[11px] text-text-muted mt-0.5">{chk.message}</p>}
                </div>
              </div>
            ))}
          </div>
          )}
        </div>
      )}
    </Card>
  );
};

export default DoctorCheckWidget;
